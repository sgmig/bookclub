# Design: create meeting locations "on the fly"

Branch: `feature/meeting-location-creation`. **✅ Implemented 2026-08-25**, built as designed below — see "Implementation notes" near the end for exactly what shipped, two bugs found along the way, and a couple of "better way, later" ideas per your instruction not to build them now.

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
4. `Location` gets a privacy flag (`is_private`), and private locations' sensitive details get redacted when their creator leaves the club that uses them — see "Privacy" section below. Added after talking through the `created_by` `on_delete` question: deleting a *user account* is rare and already handled (`SET_NULL`), but a member simply *leaving a club* while keeping their account is common, and today nothing stops every future member of that club from seeing a past member's home address forever.

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
is_private = models.BooleanField(
    default=True,
    help_text="Private locations (e.g. a member's home) have their address "
               "and access details redacted once the creator leaves the club.",
)
```

- **`created_by` nullable**: existing `Location` rows (seeded via `populate_locations`, or added through the admin) have no owner and can't be backfilled with a real one. New locations created through this feature will always set it.
- **`created_by` uses `SET_NULL` rather than `CASCADE`**: a location can be attached to a club's meetings independently of who created it (mirrors how `ClubMeeting.location` itself is `SET_NULL`). Deleting the creating user's *account* shouldn't retroactively break meeting history for the whole club — confirmed, this part of the original question is settled.
- **`is_private` defaults to `True`**: privacy-safe default. If someone quick-adds a location and forgets to mark a public café as public, the worst case is that its address gets redacted later and someone has to re-add it — annoying, but not a privacy leak. The reverse default (defaulting to public) risks the actual bad outcome: an address that should've been protected stays visible. Set via a checkbox on the create-location modal, defaulting checked.

## Privacy: redacting private-location details when a member leaves

The scenario this protects against: a member hosts meetings at their home, quick-adds it as a location, marks it private; later they leave the club, but their address stays fully visible to every member who joins afterward, forever, because nothing about `Location`/`ClubLocation` is tied to the creator's *membership status* — only to their account existing at all.

**What "leaving" means today, concretely.** There's no dedicated "leave club" / "remove member" flow yet (see `docs/ARCHITECTURE.md`). Membership changes happen two ways right now:
1. Via the Django admin (`ClubMembershipAdmin` / the `ClubMembershipInline` on `ClubAdmin`) — can edit `is_active` or delete the row outright.
2. Via `ClubForm`'s `members` field on the club edit page — this is a plain `ManyToManyField` widget; removing someone from the list calls `.set()` under the hood, which **hard-deletes their `ClubMembership` row** (not a soft `is_active=False`). So in practice, membership removal today *is* row deletion, even though `is_active` exists on the model as if it were meant to be the soft-delete mechanism. Worth knowing since it affects what event we hook into.

**Proposed trigger.** A signal receiver on `ClubMembership`:
- `post_delete` — covers both admin deletion and the `ClubForm` `.set()` path above (today's only real "leave" mechanisms).
- Also handle `is_active` flipping from `True` to `False` via a save-time check, so this doesn't silently stop working the day a future "leave club" flow switches to soft-delete instead of hard-delete.

**What redaction does**, when a membership for user `U` in club `C` is removed/deactivated: for every `Location` where `created_by = U`, `is_private = True`, and linked to `C` via `ClubLocation` — clear `address`, `access_details`, and `description`, keeping only `name`. This matches what you described: the location stays findable/nameable in meeting history ("met at Jane's place") without exposing how to actually get there. No new "redacted" flag needed — "no address on a private location" *is* the redacted state, derivable rather than stored.

**What happens to the location afterward:**
- Past `ClubMeeting` rows that already point to it are untouched — they still show the name.
- It should stop being selectable for *new* meetings (nobody has the address to host there anymore): `ClubMeetingForm.location`'s queryset needs to exclude locations that are private and have no address. I'll implement this as a queryset filter, not a deletion of the `ClubLocation` link, so the name still shows up correctly in old meeting history rather than becoming an orphaned FK.

**Known edge case, not solved here:** `address`/`access_details` live once on the `Location` row, not per-club. If a private location were ever attached to *multiple* clubs (not something this feature's own flow can produce — it only ever links to the one club it was created for — but technically possible via manual admin action), redacting it because the creator left *one* of those clubs would also blank it for the other(s), even if the creator is still active there. Flagging rather than over-building a per-club-visibility layer for a case the actual feature doesn't create.

## Proposed UX flow

Reusing the app's existing "quick-create modal" pattern rather than inventing a new one — this is the same shape already used for book ratings (`clubs/static/clubs/js/book_rating.js` + `books/static/books/js/book_rating_list/book_rating_list_buttons.js`) and reading-list items (`add_reading_list_item_modal.html`):

1. On the meeting create/update form, add a "+ Add new location" button next to the `location` field (same visual treatment as the existing unwired "+ Add new book" button).
2. Clicking it `fetch()`s a small partial view rendering an empty `LocationForm` (new form — `locations/forms.py` is currently just an unused stub with a single import, so this is its first real content) into a Bootstrap modal, and shows it. No page navigation — the rest of the in-progress meeting form (date, discussed books, notes) is preserved.
3. Submitting the modal `fetch()`-POSTs the form data (as `FormData`, CSRF header via the existing `getCSRFToken()` helper) to the locations API, same mechanic as the book-rating modal's submit handler.
4. On success, the API returns the created location as JSON. JS appends a new `<option>` to the `location` select2 widget and selects it (standard `django-autocomplete-light`/select2 pattern: `new Option(name, id, true, true)` + `trigger('change')`), closes the modal, and shows a success toast (`showBootstrapToast`, already used elsewhere).
5. The meeting form itself is submitted normally afterward, by the user, with the new location now selected.

## Proposed backend changes

- **`locations/forms.py`**: add `LocationForm` (`ModelForm` over `name`, `description`, `address`, `access_details`, `is_private`, the last as a checkbox defaulting checked) — mirrors `ClubForm`/`ReadingListForm`.
- **New template view** (small `FormView`, e.g. `LocationCreateModalView` in `locations/views.py`) that renders the modal partial (form only, no results/search — simpler than `GoogleBooksSearchForm`-based modals). Needs to know which club it's being created for, so the URL is club-scoped: `clubs/<club_id>/location/create-modal/` (lives under `clubs` urls since it's about a club-scoped location, same reasoning as `ReadingListItemAddBookView` living in `clubs` despite touching `books`).
- **API**: extend the existing `LocationsViewSet` (`locations/views.py`, currently just a bare `ModelViewSet`) the same way `BookRatingViewSet`/`ReadingListItemViewSet` already split create vs. read serializers:
  - `LocationCreateSerializer`: `name`, `description`, `address`, `access_details`, `is_private`, plus a write-only `club_id` (`PrimaryKeyRelatedField`).
  - `perform_create()`: set `created_by=self.request.user`; if `club_id` was provided, also `ClubLocation.objects.get_or_create(club=club, location=location)`.
  - This keeps location creation on a single `POST /locations/api/location/` call (matching the "submit modal → one API call → JSON back" shape the JS pattern above expects), rather than two round-trips.
- **`clubs/signals.py`** (new): `post_delete` receiver on `ClubMembership`, plus a `pre_save`/`post_save` pair detecting `is_active` transitioning to `False`, both calling a shared `redact_private_locations(user, club)` helper (probably lives on `Location`'s manager, e.g. `Location.objects.redact_for_departed_member(user, club)`) implementing the redaction described above.
- **`ClubMeetingForm.location`**: extend the existing club-scoped queryset filter to also exclude redacted private locations (`is_private=True` and blank `address`) from the choices offered for *new* meetings.
- **Migration**: add nullable `created_by` and `is_private` (default `True`) to `Location`.

## Permissions

Updated 2026-08-10: `docs/PERMISSIONS_DESIGN.md` landed and merged (both phases) since this doc was first written. Two things this changes:

- `ClubMeetingCreateView` is no longer an open concern — it now requires club membership via `ClubMemberRequiredMixin`, same as everything else. The note that used to be here about it having no check at all is resolved.
- There's now a proven, working pattern to copy rather than build from scratch: `clubs/permissions.py::IsClubMemberForMeeting` for the template-view-adjacent DRF check, and `ClubMemberRequiredMixin` (`clubs/mixins.py`) for the new modal-loading template view. The new location-creation endpoint should follow the same shape — see the implementation plan below.

## Open questions before I implement

1. ~~**Who can add a location to a club?**~~ — resolved by precedent. The permissions work settled on "any club member" everywhere else in the app (club update/delete, meeting CRUD, reading lists) rather than introducing the first admin-only gate. Applying the same rule here for consistency.
2. ~~`created_by` on_delete behavior~~ — resolved, `SET_NULL`.
3. ~~Should the inline-created location be usable only by this club, or also visible to other clubs?~~ — went with "only this club" as designed (matches the ask literally, and avoids the multi-club redaction edge case). No decision needed before implementing since nobody pushed back.
4. ~~Should users be able to edit/deactivate a location they created?~~ — no, no location edit UI built in this branch, as planned. Still deferred to the dashboard tab.
5. ~~Redaction scope~~ — implemented as `address` + `access_details` + `description` all cleared, keeping only `name`, as proposed.
6. ~~Manual early redaction~~ — not built, as planned. Still a candidate future ask.

## Non-goals for this branch

- The dashboard "Locations" tab (deferred, per above).
- Google Maps integration (already deferred in `docs/RECOMMENDATIONS.md`, needs coordinate fields on `Location` first).
- Editing or deleting existing `ClubLocation` links (only creation, via the new inline flow).
- Manual/early redaction (open question #6 above) — only the automatic on-leave trigger.
- A dedicated "leave club" / "remove member" flow — out of scope here; the redaction signal is built to work with however membership removal happens *today* (hard delete via the admin or `ClubForm`), and to keep working if that flow is built later.

## Implementation notes (2026-08-25)

Built exactly as designed above — mixins/permissions reused directly rather than rebuilt, Create/Detail serializer split matching `BookRatingViewSet`/`ReadingListItemViewSet`, modal markup and JS mirroring the book-rating modal's fetch-inject-show / fetch-submit shape down to the naming conventions (`open-*-modal-btn` class, `data-*-modal-url`/`data-*-api-url` attributes, `#*ModalContent` injection target). Verified end-to-end with a real browser (Playwright, driven headless) — login → open meeting form → "+ Add new location" → fill modal → submit → new option appears selected in the dropdown → submitting the meeting form itself succeeds — screenshots and script in the session scratchpad if useful later.

**Two real bugs found and fixed along the way, not part of the original design:**
1. `Location.is_private` had no `blank=True`, so its auto-generated form checkbox defaulted to `required=True` — a user could check it but never *uncheck* it (mark a location public) without hitting a validation error. Added `blank=True` (new migration `0003_alter_location_is_private`; `blank` has no DB-level effect, but Django still tracks it in migration state).
2. An existing test (`ClubMeetingFormLocationTests.test_location_choices_limited_to_club_locations`) built its fixture location with no address, which — now that `is_private` defaults to `True` — made it look exactly like a redacted location and get correctly excluded by the new queryset filter. Fixed the fixture (gave it a real address and explicit `is_private=False`), not the filter; the filter was doing exactly what it's supposed to.

**Revised after review (2026-08-25): split location-creation into two endpoints, one per app.** The first version of this PR put the whole thing behind a single `locations:api-location-list` POST — `LocationsViewSet.perform_create()` created the `Location` *and* the `ClubLocation` link in one call, with a `locations/permissions.py::IsClubMemberForLocationCreate` class that had to import `clubs.models.Club` to do the membership check. Called out in review: that's backwards. `ClubLocation` is a `clubs` model — attaching a location to a club is a `clubs`-owned operation, not a `locations` one — and the single-endpoint version made `locations` depend on `clubs` in three places (`permissions.py`, `serializers.py`, `views.py`), reversing the only dependency direction this codebase has ever had (`clubs` → `locations`, never the other way).

The fix follows a precedent that was already sitting in the codebase and should have been the template from the start: `BookViewSet.create_from_search` (in `books`, zero club awareness, `IsAuthenticated` only) + `ReadingListItemViewSet.create()` (in `clubs`, links an *existing* book to a reading list, membership-checked). Locations now work the same way:

- `LocationsViewSet.create()` (`locations`) — back to `IsAuthenticated` only, no `club` field, no `ClubLocation` side effect. `locations/permissions.py` is gone entirely; the app has zero imports from `clubs` again.
- `ClubLocationViewSet.create()` (new, `clubs/views.py`) — takes existing `club` + `location` ids, membership-checked, creates the `ClubLocation` row. Reuses `IsClubMember` directly (renamed from `IsClubMemberForMeeting`, since it now guards two models — `ClubMeeting` and `ClubLocation` both expose a direct `.club`, so the same `has_object_permission` works unmodified for both).
- `LocationCreateModalView` moved from `locations/views.py` to `clubs/views.py` too (template moved with it, `clubs/templates/clubs/partials/`) — it was always fundamentally a club-access-gating view (membership check on a `club_id` URL param), just rendering a `locations` form. Matches where `ReadingListItemAddBookView` already lives despite rendering a `books` form.
- The frontend went from one POST to two, chained: create the `Location`, then `POST` `{club, location}` to `clubs:api-club-location-list`. More round-trips, correct app boundaries. `location_create_modal.js` updated accordingly.

Full test suite re-run after the split (128/128), and the browser walkthrough re-verified end to end against the new two-call flow — same result, no console errors.

### Ideas for later, not built here (per your instruction — documenting rather than doing)

- **The "dismiss on click, before the response comes back" modal pattern has a real UX gap, and I just replicated it rather than fixing it.** Every quick-create modal in this app (book rating, and now this one) puts `data-bs-dismiss="modal"` directly on the Save button, so the modal closes immediately regardless of whether the API call actually succeeds — a validation failure just shows a generic toast ("An unexpected error occurred") with no way to see what was wrong or fix and resubmit without reopening the modal from scratch. Worth fixing app-wide at some point: wait for a successful response before dismissing, and surface field-level errors inline in the modal on failure. Didn't fix it here since the instruction was to match the existing pattern, not improve it — but it's the same gap in both places now, so worth doing once, everywhere.
- **The fetch-modal / fetch-submit JS is copy-pasted per feature** (`book_rating_list_buttons.js`, now `location_create_modal.js`) with near-identical open/inject/show and submit/fetch/toast logic, differing only in element IDs and URLs. A small shared utility (e.g. `openFetchModal(triggerSelector, contentUrl, contentElId, modalElId)` / `bindModalSubmit(buttonId, formId, onSuccess)`) would remove most of that duplication for whatever quick-create modal comes next. Three occurrences of the same shape (rating, reading-list-item search, now location) feels like the point where extracting it stops being premature.
- **First use of Django signals in this codebase** — there was no existing convention to match for "react to a model change elsewhere," so `clubs/signals.py` uses the standard idiomatic approach (`pre_save`+`post_save` pairing to detect a field flip, `post_delete` for the hard-delete path), wired via `AppConfig.ready()`. Flagging simply because it's a new mechanism in the app, not because it's uncertain — `post_delete`/`post_save` are the only way to reliably catch admin bulk-deletes and queryset-level `.delete()` calls, which a `Model.delete()` override would miss.
