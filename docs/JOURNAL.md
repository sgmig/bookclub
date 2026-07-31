# Journal — bug fixes & test coverage (branch `fix/small-bugs-and-tests`)

Scope: fix the "small bugs" flagged in `docs/RECOMMENDATIONS.md` §1, and add automated test coverage for existing behavior. No new features. Full diff: `git diff main...fix/small-bugs-and-tests`.

## How this went

I fixed the bugs from the recommendations doc first, then wrote tests against the *existing* behavior described in `docs/ARCHITECTURE.md`. Writing that test coverage surfaced three more bugs that weren't in the original list — one of them a full crash (500) for anonymous users on a common path. Those are documented below alongside the originally-planned fixes. Everything was run against the real dev Postgres database configured in `.env` (`manage.py test` creates/tears down a throwaway `test_<dbname>`); all 64 tests pass, `manage.py check` is clean, and `makemigrations --check` reports no pending model changes.

## Bugs fixed

### From the recommendations doc

1. **Club CRUD success URLs.** `ClubCreateView`/`ClubUpdateView`/`ClubDeleteView` called `reverse_lazy("club_list")`, which doesn't exist (the registered name is the namespaced `clubs:club-list`) — every successful create/update/delete raised `NoReverseMatch`. Fixed to `reverse_lazy("clubs:club-list")`.
   `clubs/views.py`

2. **`ClubLocation` uniqueness constraint was inert.** Its `UniqueConstraint` was declared as a bare class attribute instead of inside `class Meta`, so Django never applied it. Moved into `Meta` and generated `clubs/migrations/0004_clublocation_unique_location_for_club.py`. Applied it against the dev DB to confirm it doesn't conflict with any existing rows (it didn't).
   `clubs/models.py`

3. **Missing `LoginRequiredMixin` on club CRUD views.** `ClubListView`, `ClubDetailView`, `ClubCreateView`, `ClubUpdateView`, `ClubDeleteView` had no login gate at all, unlike the rest of the app. Added `LoginRequiredMixin` to all five.
   `clubs/views.py`

4. **Stray debug `print()`s**, plus a real bug hiding behind one of them: `ReadingListItemAddBookView.form_valid` only assigned `results` inside `if response:` — a failed/empty Google Books search (`search_volumes` returns `{}` on failure) would hit `UnboundLocalError` on the next line, `print(f"Found {len(results)} results")`. Initialized `results = []` up front and dropped the prints. Also removed prints in `books/views.py` (`BookSearchView`, `BookSearchViewModule`, `BookRatingUpdateView`, `BookRatingModalView`) and two leftover debug prints in `books/integrations/google_books.py::parse_year_from_publication_date` (not explicitly listed in the recommendations doc, but the same category of leftover debug output, so cleaned up alongside the rest).
   `clubs/views.py`, `books/views.py`, `books/integrations/google_books.py`

5. **No dependency manifest.** Added `requirements.txt` (runtime deps) and `requirements-dev.txt` (seed-data/interactive-shell-only deps: `Faker`, `ipython`, and their transitive deps), generated from the working `.djangoenv` virtualenv and split by actual usage.
   `requirements.txt`, `requirements-dev.txt` (repo root)

### Found while writing tests, fixed because they're outright broken (not new functionality)

These came up because a test written against the *documented* behavior failed against the *actual* behavior. In each case the code clearly intended one thing and did another:

6. **`ClubCreateView` never set `created_by`.** `ClubForm.Meta.fields` is `["name", "description", "members"]` — `created_by` isn't on the form, and unlike `ReadingListCreateView` (which does this correctly), `ClubCreateView` had no `form_valid()` to set it from `request.user`. Since `Club.created_by` is a required FK, **every attempt to create a club through the form raised `IntegrityError`** — club creation was completely broken, independent of bug #1 above. Added `form_valid()` setting `form.instance.created_by = self.request.user`, mirroring the existing `ReadingListCreateView` pattern.
   `clubs/views.py`

7. **`ClubBookRatingListView`'s membership check was dead code.** `get_queryset()` returned `HttpResponseForbidden(...)` for non-members — but a `ListView`'s `get_queryset()` return value is expected to be a queryset, not an `HttpResponse`; returning one there doesn't short-circuit the request. The view rendered a `200` for non-members instead of denying access. Moved the club/book lookup and the membership check into `dispatch()` (the pattern already used correctly by `ClubMeetingDetailView` etc. elsewhere in the same file), so the forbidden response is now actually returned to the client.
   `clubs/views.py`

8. **`BookRatingCreateView` and `BookRatingModalView` crashed (500) for anonymous users.** Both override `dispatch()` and, when a `book_id` is present in the query string, run `BookRating.objects.filter(book=..., user=self.request.user)` *before* calling `super().dispatch()` — which is what would normally trigger `LoginRequiredMixin`'s redirect. For an anonymous request, `request.user` is an `AnonymousUser`, and using it as a FK lookup value raises `TypeError: Field 'id' expected a number but got <AnonymousUser>`, an unhandled 500. Added an explicit `if not request.user.is_authenticated: return self.handle_no_permission()` guard at the top of both `dispatch()` methods, before any DB lookup runs. `handle_no_permission()` is the same method `LoginRequiredMixin` itself calls, so the resulting redirect-to-login behavior is identical to what the mixin already promises everywhere else.
   `books/views.py`

## Found while writing tests, deliberately *not* fixed (out of scope for this pass)

Flagging these rather than fixing them silently, since fixing them would mean either touching several views at once (bigger than "small bug") or changing existing dedup semantics that are already called out as a known limitation in the code:

- **Anonymous users get a bare 403 instead of a login redirect on several views** (`ClubMeetingDetailView`, `ClubMeetingPartialDetailView`, `ReadingListPartialDetailView`, `ReadingListItemRowView`). Same root cause as bug #8 above (custom `dispatch()` logic runs before `super().dispatch()`, so `LoginRequiredMixin` never gets a chance to redirect) — but here the custom logic itself doesn't crash for an `AnonymousUser` (`user not in queryset` and `user != creator` are both safe comparisons), it just produces the wrong status code/UX. Access is still correctly denied, just not consistently. This is exactly the inconsistency flagged in `docs/RECOMMENDATIONS.md` §2 ("Permissions review") and `docs/ARCHITECTURE.md` finding #3 — recommend fixing it once, as a shared mixin, during that pass rather than patching four call sites piecemeal here. Covered by `clubs.tests.ClubMeetingAccessTests.test_anonymous_user_is_denied_access`, which documents (rather than asserts an ideal for) the current `403`.
- **`Book.filter_by_authors_and_title` false-positives on a partial author match.** Already flagged by a `# TODO` in `books/models.py` itself: `num_authors` is computed as `Count("authors")` *after* the queryset was already filtered down to `authors__in=[...]`, so it counts only the authors that survived the join filter, not the book's true total author count. A book with two authors currently matches a lookup for just one of them. This affects the Google-Books-import dedup path (`BookViewSet.create_from_search`) — worth a real fix, but it changes matching semantics (a "small bug fix" risks silently changing which books get deduped vs. duplicated), so it's left as-is and documented via `books.tests.BookModelTests.test_filter_by_authors_and_title_false_positive_on_partial_author_match`.
- **DRF anonymous requests return `403`, not `401`,** on the `books` and `locations` API viewsets. This turned out to be correct-by-design DRF behavior (not a bug): `SessionAuthentication` is checked before `BasicAuthentication` in the default authenticator list, and since `SessionAuthentication.authenticate_header()` returns `None`, DRF's exception handler downgrades `NotAuthenticated` (401) to `403`. No code change; just noting it since it's easy to assume 401 and be wrong.

## Tests added

All five apps had empty (boilerplate) `tests.py` files before this branch. Added 64 tests total, run via `manage.py test`:

| App | File | Coverage |
|---|---|---|
| `accounts` | `accounts/tests.py` | `CustomUserManager` (email normalization, required-email validation, superuser flag enforcement), `CustomUser` model helpers (`__str__`, `get_full_name`, `get_short_name`), signup view (render, create, redirect-if-already-authenticated), login view (render, successful login, redirect-if-already-authenticated) |
| `books` | `books/tests.py` | `Author.get_or_create_authors_from_names` (dedup, title-casing, blank-skipping), `Book.filter_by_authors_and_title` (matching + the documented false-positive limitation), `Book.list_authors`, `BookRating` unique-per-user-per-book constraint, `parse_year_from_publication_date` (full date / year-month / year-only / unparseable), `BookRatingCreateView` (create, redirect-to-update when a rating already exists, anonymous redirect), `BookViewSet.create_from_search` (create vs. dedupe-to-existing, required-fields validation, anonymous rejection) |
| `clubs` | `clubs/tests.py` | `Club.next_meeting` (ignores past, picks soonest), `Club.get_rated_books` (counts only club members' ratings), `ClubLocation` uniqueness constraint, club CRUD (login-required, create/update/delete now redirect correctly — regression coverage for bugs #1/#3/#6), reading-list access control (club-member vs. personal-list-creator branches, both allow and forbid cases), `ReadingListForm`'s club-queryset scoping, club-meeting access control (member/outsider/anonymous), `ClubMeetingForm`'s location-queryset scoping to the club's linked locations, `ClubBookRatingListView` (member-only filtering — regression coverage for bug #7), `ReadingListItemViewSet` API (create sets `added_by`, `reading_list_id` filtering) |
| `locations` | `locations/tests.py` | `Location.__str__`, `LocationsViewSet` API (auth required, list, create) |
| `userdashboard` | `userdashboard/tests.py` | `UserDashboardView` (login required, context scoped to the logged-in user only — clubs/reading lists/ratings), `UserClubListView` (login required, scoped to the user's own clubs) |

Run with:
```
cd clubdelectura
python manage.py test
```

## Files changed

```
Modified:
  clubdelectura/clubs/models.py
  clubdelectura/clubs/views.py
  clubdelectura/books/views.py
  clubdelectura/books/integrations/google_books.py
  clubdelectura/accounts/tests.py
  clubdelectura/books/tests.py
  clubdelectura/clubs/tests.py
  clubdelectura/locations/tests.py
  clubdelectura/userdashboard/tests.py

Added:
  clubdelectura/clubs/migrations/0004_clublocation_unique_location_for_club.py
  requirements.txt
  requirements-dev.txt
  docs/ARCHITECTURE.md
  docs/RECOMMENDATIONS.md
  docs/JOURNAL.md (this file)
```

Not touched in this branch (pre-existing untracked files, unrelated to this task): `.sample_data/`, `clubdelectura/locations/forms.py` (empty stub), `to_do.txt`.
