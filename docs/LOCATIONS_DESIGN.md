# Design: create meeting locations "on the fly"

Branch: `feature/meeting-location-creation`. Design-only — no code changes yet.

## The ask

From the conversation that kicked this off:

> When creating a new meeting we should be able to create a location "on the fly". Since the meeting is associated to a club, this would automatically list it as a club location. It should also be associated to the user. Eventually, in the dashboard, we would add a locations tab where a user could see the locations they created and their club locations.

## Current state (baseline)

Covered in `docs/ARCHITECTURE.md`, summarized here for context:

- `Location` (`locations/models.py`): `name`, `description`, `address`, `access_details`. No owner field.
- `ClubLocation` (`clubs/models.py`): join table, `(club, location)`, unique — the pool of locations a club can hold meetings at.
- `ClubMeetingForm.location`: a `ModelChoiceField` whose queryset is restricted to `Location`s already linked to the club via `ClubLocation` — but **there is no UI anywhere to create that link**, only the Django admin. In practice, a club's location dropdown is empty until someone manually adds rows via `/admin/`. This is the gap this branch closes.
- The meeting form template (`clubs/club_meeting_form.html`) already has a **stub button** for exactly this shape of feature, unwired: `+ Add new book`, `data-bs-toggle="modal" data-bs-target="#"` — target `#` goes nowhere. It sits next to `discussed_books`, not `location`, but it's evidence the app's own author intended an inline-create pattern here and didn't get to it. We're building the location version of the same idea.

## Scope for this branch

**In scope:**
1. `Location` gets an owner (`created_by`).
2. An inline "create a location" flow reachable from the meeting create/update form.
3. Creating a location this way automatically links it to the meeting's club via `ClubLocation`.

**Explicitly deferred** (per your "eventually"): the dashboard "Locations" tab showing a user's created locations + their clubs' locations. Nothing here should require a second migration to support it later — `created_by` on `Location` plus the existing `ClubLocation` join table are already sufficient to build that view whenever it's prioritized (`Location.objects.filter(created_by=user)` and `Location.objects.filter(club_locations__club__in=user.clubs.all())`).

## Proposed data model change

Add to `Location`:

```python
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="locations",
)
```

- **Nullable**: existing `Location` rows (seeded via `populate_locations`, or added through the admin) have no owner and can't be backfilled with a real one. New locations created through this feature will always set it.
- **`SET_NULL` rather than `CASCADE`**: a location can be attached to a club's meetings independently of who created it (mirrors how `ClubMeeting.location` itself is `SET_NULL` — a location's lifecycle shouldn't be tied to one user's account). Deleting the creating user's account shouldn't retroactively break meeting history for the whole club.
- One open question below on whether this is the right `on_delete` choice for your intent — flagging rather than assuming.

## Proposed UX flow

Reusing the app's existing "quick-create modal" pattern rather than inventing a new one — this is the same shape already used for book ratings (`clubs/static/clubs/js/book_rating.js` + `books/static/books/js/book_rating_list/book_rating_list_buttons.js`) and reading-list items (`add_reading_list_item_modal.html`):

1. On the meeting create/update form, add a "+ Add new location" button next to the `location` field (same visual treatment as the existing unwired "+ Add new book" button).
2. Clicking it `fetch()`s a small partial view rendering an empty `LocationForm` (new form — `locations/forms.py` is currently just an unused stub with a single import, so this is its first real content) into a Bootstrap modal, and shows it. No page navigation — the rest of the in-progress meeting form (date, discussed books, notes) is preserved.
3. Submitting the modal `fetch()`-POSTs the form data (as `FormData`, CSRF header via the existing `getCSRFToken()` helper) to the locations API, same mechanic as the book-rating modal's submit handler.
4. On success, the API returns the created location as JSON. JS appends a new `<option>` to the `location` select2 widget and selects it (standard `django-autocomplete-light`/select2 pattern: `new Option(name, id, true, true)` + `trigger('change')`), closes the modal, and shows a success toast (`showBootstrapToast`, already used elsewhere).
5. The meeting form itself is submitted normally afterward, by the user, with the new location now selected.

## Proposed backend changes

- **`locations/forms.py`**: add `LocationForm` (`ModelForm` over `name`, `description`, `address`, `access_details`) — mirrors `ClubForm`/`ReadingListForm`.
- **New template view** (small `FormView`, e.g. `LocationCreateModalView` in `locations/views.py`) that renders the modal partial (form only, no results/search — simpler than `GoogleBooksSearchForm`-based modals). Needs to know which club it's being created for, so the URL is club-scoped: `clubs/<club_id>/location/create-modal/` (lives under `clubs` urls since it's about a club-scoped location, same reasoning as `ReadingListItemAddBookView` living in `clubs` despite touching `books`).
- **API**: extend the existing `LocationsViewSet` (`locations/views.py`, currently just a bare `ModelViewSet`) the same way `BookRatingViewSet`/`ReadingListItemViewSet` already split create vs. read serializers:
  - `LocationCreateSerializer`: `name`, `description`, `address`, `access_details`, plus a write-only `club_id` (`PrimaryKeyRelatedField`).
  - `perform_create()`: set `created_by=self.request.user`; if `club_id` was provided, also `ClubLocation.objects.get_or_create(club=club, location=location)`.
  - This keeps location creation on a single `POST /locations/api/location/` call (matching the "submit modal → one API call → JSON back" shape the JS pattern above expects), rather than two round-trips.
- **Migration**: add nullable `created_by` to `Location`.

## Permissions (needs a decision — see below)

The new endpoint should check that the requesting user is actually a member of the club they're attaching a location to, before creating the `ClubLocation` link — this is a new API surface, so it should be built with that check from the start rather than inheriting the app's existing "API only checks `IsAuthenticated`" gap (tracked separately in `docs/RECOMMENDATIONS.md` §2 "Permissions review").

Worth noting while we're here: `ClubMeetingCreateView` itself currently has **no club-membership check at all** (only `LoginRequiredMixin`) — any logged-in user can create a meeting for any club by hitting its URL directly, not just members. That's a pre-existing gap, not something introduced by this feature, and I'd rather flag it than silently fix it mid-feature-branch (it belongs with the other permissions-consolidation work). But it's relevant context for deciding how strict to make the new location endpoint.

## Open questions before I implement

1. **Who can add a location to a club?** Any club member (consistent with how any member can currently add reading-list items), or club admins only (`ClubMembership.is_admin` exists on the model but isn't enforced anywhere in the app today)? I'd default to **any member**, for consistency with the rest of the app's current permission granularity — but this is your call.
2. **`created_by` on_delete behavior.** Proposing `SET_NULL` (location survives, ownership just clears) — confirm that matches your intent, versus e.g. `CASCADE` (deleting a user deletes locations only they created, even if a club is actively using one for meetings) or `DO_NOTHING` (matches `Club.created_by`'s current, TODO-flagged choice).
3. **Should the inline-created location be usable only by this club, or should it also become visible to other clubs the user belongs to as a "suggested" location?** The ask says "automatically list it as a club location" (singular, the meeting's club) — I'm proposing exactly that and nothing more, but flagging in case you meant something broader.
4. **Should users be able to edit/deactivate a location they created** (e.g. fix a typo in the address) from anywhere yet, or is that explicitly part of the deferred dashboard tab? I'd assume the latter — no location edit UI in this branch.

## Non-goals for this branch

- The dashboard "Locations" tab (deferred, per above).
- Google Maps integration (already deferred in `docs/RECOMMENDATIONS.md`, needs coordinate fields on `Location` first).
- Fixing `ClubMeetingCreateView`'s missing membership check (noted above, belongs to the permissions-consolidation pass).
- Editing or deleting existing `ClubLocation` links (only creation, via the new inline flow).
