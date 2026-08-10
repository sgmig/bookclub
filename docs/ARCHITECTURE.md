# BookClub (clubdelectura) — Current State

A Django 5.1 application for managing book clubs: creating clubs, reading lists, meetings, and book ratings. Built with server-rendered Django templates (Bootstrap 5) plus a parallel Django REST Framework API layer used mainly for HTMX/JS-driven partial updates (add/remove reading list items, meetings, ratings).

> Originally written 2026-08-01, updated 2026-08-07 after merging branch `fix/small-bugs-and-tests` (PR #1). That branch fixed several of the issues originally documented here and added the project's first test suite — see `docs/JOURNAL.md` for the full change log. This doc has been updated to reflect current (fixed) behavior; items still open are called out explicitly below.

## Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.1.7 |
| Database | PostgreSQL (`psycopg2`) |
| API | Django REST Framework 3.15 + `drf-spectacular` (OpenAPI schema, Swagger UI) |
| Forms/UI | `django-crispy-forms` + `crispy-bootstrap5`, Bootstrap 5.3 (via CDN), jQuery (via CDN) |
| Autocomplete | `django-autocomplete-light` (`dal`, `dal_select2`) for author/book/reading-list-item pickers |
| Config | `python-dotenv`, secrets/DB settings pulled from a `.env` file |
| Seed data | Custom `manage.py` management commands per app (`populate_*`), plus `Faker` for fake data generation |
| Test data | `.sample_data/` — CSV/XLSX exports (Goodreads, Amazon reviews, best-seller lists) used to seed the DB, not part of the app runtime |

Dependencies are pinned in `requirements.txt` (runtime) and `requirements-dev.txt` (seed-data/interactive-shell tools: `Faker`, `ipython`), both at the repo root — install with `pip install -r requirements.txt` (add `-r requirements-dev.txt` for local dev). No `pyproject.toml`/lockfile beyond that.

## App structure

The project root is `clubdelectura/` (contains `manage.py`), with the Django project package also named `clubdelectura/` (`settings.py`, root `urls.py`, `wsgi.py`/`asgi.py`). Five installed local apps:

```
clubdelectura/
├── accounts/       # Custom user model, auth (login/signup/logout)
├── locations/      # Meeting locations (address, access details)
├── books/          # Books, Authors, Ratings, Google Books integration
├── clubs/          # Clubs, Memberships, Reading Lists, Meetings
└── userdashboard/  # Logged-in user's landing dashboard
```

Root URLs (`clubdelectura/urls.py`) mount each app under a prefix:

| Prefix | App | Notes |
|---|---|---|
| `/` | `clubs.views.IndexView` | Public landing page |
| `/admin/` | Django admin | |
| `/accounts/` | `accounts` | login, signup, logout |
| `/readers/` | `userdashboard` | note: URL prefix (`readers`) doesn't match the app's own namespace (`user_dashboard`) or app label (`userdashboard`) — three different names for the same app |
| `/books/` | `books` | book CRUD, ratings, Google Books search, autocomplete, DRF API under `/books/api/` |
| `/clubs/` | `clubs` | club/reading-list/meeting CRUD, DRF API under `/clubs/api/`, OpenAPI schema + Swagger UI |
| `/locations/` | `locations` | DRF API only, under `/locations/api/` (no template views) |

## Data model

### accounts
- **`CustomUser`** (`AUTH_USER_MODEL`) — email-based auth (no username field), `first_name`, `last_name`, standard `is_active`/`is_staff` flags, custom manager (`CustomUserManager`) with sync/async user creation.

### locations
- **`Location`** — `name`, `description`, `address`, `access_details`. Flat model, no geocoordinates, no owner/club link at this level (that link lives in `clubs.ClubLocation`).

### books
- **`Author`** — `name` only (matches what Google Books API returns), with a case-insensitive index (`Lower(name)`) for search/autocomplete. Class method `get_or_create_authors_from_names` normalizes and dedupes author names.
- **`Book`** — `title`, `year` (nullable), `authors` (M2M to `Author`). Helper `filter_by_authors_and_title` finds an existing book matching a title and an exact set of authors (used to dedupe when importing from Google Books).
- **`BookRating`** — `book` FK, `user` FK, `rating` (float 0–10), `comment`, `created_at`. Unique constraint on `(user, book)` — one rating per user per book.

### clubs
- **`Club`** — `name`, `description`, `created_by` (FK, `on_delete=DO_NOTHING`), `members` (M2M to user through `ClubMembership`). Methods: `next_meeting()`, `get_rated_books()` (books rated by club members, annotated with avg rating + rating count).
- **`ClubMembership`** — through-table: `user`, `club`, `is_admin` (unused so far), `joined_at`, `is_active`.
- **`ReadingList`** — `name`, optional `club` FK (nullable — supports personal, club-less lists), `created_by`, `books` M2M through `ReadingListItem`.
- **`ReadingListItem`** — `reading_list` FK, `book` FK, `added_by` FK, unique per `(reading_list, book)`.
- **`ClubLocation`** — join table associating a `Club` with one or more `Location`s (the pool of places a club can hold meetings at). Unique per `(club, location)`, enforced at the DB level via migration `0004_clublocation_unique_location_for_club`.
- **`ClubMeeting`** — `club` FK, `location` FK (`SET_NULL`, optional), `date` (datetime), `discussed_books` (M2M to `ReadingListItem`, not directly to `Book` — a book must already be on a reading list to be discussed), `notes`.

### userdashboard
- No models — pure view/template layer aggregating data from `clubs` and `books`.

## Key workflows

### Authentication
- Email-based custom login (`accounts:login`), signup (`accounts:signup`, uses `BaseUserCreationForm` subclass), logout with a confirmation interstitial page. `LOGIN_REDIRECT_URL` → `/readers/dashboard`, `LOGOUT_REDIRECT_URL` → `index`.
- No password reset / email verification flow.

### Clubs
- Standard CRUD (`ClubListView/DetailView/CreateView/UpdateView/DeleteView`), all `LoginRequiredMixin`-protected and redirecting to `clubs:club-list` on success; `ClubCreateView` sets `created_by` from the logged-in user.
- `ClubDetailView` assembles members, reading lists, meetings (ordered by `-date`), next meeting, and rated books (ordered by number of ratings) into one page.
- Membership itself has no dedicated UI (no "join club" / "invite member" flow) — membership rows must currently be created via the admin or the `members` field on the club form (a plain multi-select of all users).

### Reading lists
- Can belong to a club or be personal (`club=None`).
- Creation/update forms take `user`/`club` context: if a `club_id` is passed, the club field is pre-set and disabled; otherwise the dropdown is restricted to the user's own clubs.
- Adding books to a list is split across two mechanisms: a template-rendered Google Books search form (`ReadingListItemAddBookView`) to find a book, and a DRF `ReadingListItemViewSet` API for the actual create/delete, presumably driven by JS/HTMX against the partials (`reading_list_item_row.html`, `add_reading_list_item_modal.html`).
- Access control on list detail/partial views: if the list belongs to a club, only members can view it; if personal, only the creator — enforced manually in `dispatch()`, returning `HttpResponseForbidden` (plain 403 text, not a styled page).

### Meetings
- Split date/time input (`SplitDateTimeField`) with 1-minute step.
- `location` choices are restricted to locations already associated with the club via `ClubLocation` — but there is **no UI to create a `ClubLocation`**, so in practice a club currently has an empty location dropdown unless one is added through the admin. This matches the to-do item "Add locations logic when creating new meeting."
- `discussed_books` uses an autocomplete widget scoped to the club's reading-list items (via `forward=["club"]` and a per-club autocomplete URL).
- Meeting detail/partial views check club membership before allowing access.
- No online/in-person distinction yet (also a to-do item).

### Books & ratings
- Manual book creation form, plus a Google Books search flow:
  - `books.integrations.google_books.GoogleBooksAPI` wraps the Google Books "volumes" search endpoint (title/author/publisher/subject/isbn/lccn/oclc), requires `GOOGLE_BOOKS_API_KEY`/`GOOGLE_BOOKS_API_URL` env vars, returns raw `requests.Response`.
  - `BookViewSet.create_from_search` (DRF action) takes a title + comma-separated author names (+ optional published date), normalizes them, and either finds an existing matching `Book` or creates one — used to persist a result picked from a Google Books search.
- Ratings: one per `(user, book)`, enforced by both the create-view redirect logic (redirects to update if a rating already exists) and a DB unique constraint. Both a full-page and a modal ("quick rate") flow exist. Deletion also has both a full-page and modal confirmation.
- `BookRatingListView` supports filtering by `book_id` and/or `user_id` (multi) via query params; `ClubBookRatingListView` is a club-scoped variant restricted to club members, rendering the same ratings-table partial.
- Author/Book autocomplete views (`django-autocomplete-light`) back the relevant form widgets.

### REST API
- Present for: `books` (`Book`, `BookRating`), `clubs` (`ReadingListItem`, `ClubMeeting`), `locations` (`Location`). No API for `Club`/`ClubMembership`/`ReadingList` themselves (a `ClubSerializer` exists but isn't wired to a viewset).
- All API views require `IsAuthenticated`; there's no per-object permission layer (e.g. nothing stops an authenticated user from creating a `ReadingListItem` in a reading list they don't belong to via the API — that check only exists in the template views' `dispatch()`).
- OpenAPI schema + Swagger UI are only mounted under `clubs/api/schema` (`clubs:schema`, `clubs:swagger-ui`), even though it documents the `books` and `locations` API routers too (they're on separate URL prefixes, so this works, but it's a slightly arbitrary home for the schema route).

### User dashboard
- `UserDashboardView` (template: `userdashboard/dashboard.html`) aggregates the user's clubs, reading lists, and ratings — but the template is a **static Bootstrap mockup**: the "Add Club" modal form has no `action`/submit handling, and the Edit/Delete buttons next to reading lists and ratings are inert (only the club "Edit" link is wired, and it actually links to club *detail*, not edit). This lines up with the to-do item "Modify the main user page."
- `UserClubListView` is a simple list of the user's clubs with no template beyond the default list rendering.

## Notable gaps / inconsistencies observed while reviewing

These are descriptive observations for the current-state doc; concrete suggestions are in the companion recommendations document. Items resolved by `fix/small-bugs-and-tests` are marked ✅; still-open items carry forward into `docs/RECOMMENDATIONS.md`.

1. ✅ ~~`ClubCreateView`/`ClubUpdateView`/`ClubDeleteView` reverse_lazy("club_list") NoReverseMatch~~ — fixed, now points to `clubs:club-list`. While fixing this, also found and fixed a second, deeper bug in the same flow: `ClubCreateView` never set `created_by`, so creating a club through the form always raised `IntegrityError` regardless of the redirect issue.
2. ✅ ~~`ClubLocation.constraints` declared outside `class Meta`~~ — fixed and migrated (`0004_clublocation_unique_location_for_club`).
3. ✅ **Authorization inconsistency — resolved.** All of the below are now fixed via `docs/PERMISSIONS_DESIGN.md` (`feature/club-membership-template-views`, merged 2026-08-07, and `feature/club-membership-drf-api`, 2026-08-10):
   - ✅ Club CRUD views now require login (`LoginRequiredMixin` added to all five) *and* membership (`ClubUpdateView`/`DeleteView`), via a shared `ClubMemberRequiredMixin`.
   - ✅ The DRF API layer now checks object-level membership/ownership too, not just `IsAuthenticated` — `ClubMeetingViewSet`/`ReadingListItemViewSet` via `clubs/permissions.py`, and (a related gap found along the way) `BookRatingViewSet` via `books/permissions.py::IsRatingOwnerOrReadOnly`, since any authenticated user could previously edit/delete any other user's rating.
   - ✅ `ClubMeetingDetailView`, `ClubMeetingPartialDetailView`, `ReadingListPartialDetailView`, and `ReadingListItemRowView` no longer return a bare `403` for anonymous users instead of redirecting to login — consolidated onto the same `ClubMemberRequiredMixin`/`ReadingListAccessRequiredMixin` as everything else, which checks authentication first.
   - ✅ `ClubBookRatingListView`'s membership check was previously dead code (it returned an `HttpResponse` from `get_queryset()`, which `ListView` silently ignored, so non-members actually got a `200`). Fixed by moving the check into `dispatch()`.
   - **New, still open**: any authenticated user can still `DELETE` any shared `Book` via the API — found while auditing every DRF viewset for the above, but it's a different kind of gap (no owner/club concept exists for `Book` at all, so it's a policy question, not a missing-check bug). See `docs/RECOMMENDATIONS.md` §"Permissions review".
4. **Open**: `userdashboard` app naming — URL prefix `readers/`, `app_name = "user_dashboard"`, Python package `userdashboard` — three different identifiers for one app, easy to trip over when adding new routes/links.
5. ✅ ~~Leftover `print()` debug statements~~ — removed from `books/views.py`, `clubs/views.py`, and `books/integrations/google_books.py`. One `# TODO`-flagged behavior remains open: `Book.filter_by_authors_and_title` (used by the Google Books import dedup path) can false-positive-match a book against a *subset* of its actual authors, because `num_authors` is computed from the already-filtered join rather than the book's true author count. Documented (not fixed, to avoid silently changing dedup semantics) via `books.tests.BookModelTests.test_filter_by_authors_and_title_false_positive_on_partial_author_match`.
6. ✅ ~~No automated test coverage~~ — 108 tests now exist across all five apps (see `docs/JOURNAL.md` and `docs/PERMISSIONS_DESIGN.md` for the coverage breakdown; `ClubMeeting`/`ReadingList` CRUD permission paths and the DRF viewsets' permission enforcement are now covered as of the two `feature/club-membership-*` branches). Still open: `BookRating` delete-flow template views, and `LocationsViewSet`'s write paths beyond the basics. Also worth noting: the full suite now takes 5–8 minutes against the real dev Postgres DB and had to move to background/async execution during the DRF permissions work — a faster dedicated test-DB setup (SQLite for tests, or a lightweight Postgres) is worth doing before this suite grows further.
7. ✅ ~~No `requirements.txt`/lockfile~~ — added (`requirements.txt`, `requirements-dev.txt`).
8. **Open**: the root `templates/includes/navbar.html` has a leftover Bootstrap starter-template dropdown ("Dropdown" / "Action" / "Another action") that isn't wired to anything.
