# BookClub — Recommendations & Roadmap

This document folds in the existing `to_do.txt` (unedited items are marked from **[to-do]**) alongside issues and gaps found while reviewing the codebase (see `docs/ARCHITECTURE.md` for the full current-state review). Grouped by priority, not by app, since most of the interesting work here cuts across apps.

> Updated 2026-08-07: §1 has been completed and merged (branch `fix/small-bugs-and-tests`, PR #1) — full detail in `docs/JOURNAL.md`. Kept below (struck through) for the historical record; §2 and §3 are unchanged except where noted.

## 1. Bugs to fix first (small, high-impact) — ✅ done, merged 2026-08-07

- ~~**Fix `Club` CRUD success URLs.**~~ Fixed. Also uncovered and fixed a second bug in the same flow: `ClubCreateView` never set `created_by`, so the form-based create path was completely broken (`IntegrityError`) independent of the redirect issue.
- ~~**Fix `ClubLocation`'s uniqueness constraint.**~~ Fixed and migrated.
- ~~**Add `LoginRequiredMixin` to the `Club` CRUD views.**~~ Fixed.
- ~~**Remove stray `print()` debug statements.**~~ Fixed, including the `UnboundLocalError` in `ReadingListItemAddBookView.form_valid`.
- ~~**Commit a dependency manifest.**~~ Fixed — `requirements.txt` + `requirements-dev.txt`.

Writing the first real test suite (§3 "Automated tests", also now done) surfaced two more small, genuine bugs that got fixed alongside the above even though they weren't on the original list: `ClubBookRatingListView`'s membership check was dead code (returned an `HttpResponse` from `get_queryset()`, which `ListView` silently ignores — non-members got a `200`, not a `403`), and `BookRatingCreateView`/`BookRatingModalView` crashed with an unhandled 500 for anonymous users on a `?book_id=` URL. See `docs/JOURNAL.md` for exact detail, and `docs/ARCHITECTURE.md` §"Notable gaps" for what's still open (a related-but-lower-severity 403-vs-redirect inconsistency on four other views, and a pre-existing `TODO`-flagged false positive in `Book.filter_by_authors_and_title`).

## 2. From `to_do.txt`, organized with context

### Book ratings views
- ~~Update line on create/edit via modal~~ — **[to-do: done]**
- ~~Autocomplete filter~~ — **[to-do: not priority, deferred]**
- **Fix "Add rating" button destination.** **[to-do]** Today `BookRatingCreateView`/`BookRatingModalView` redirect to `books:book-detail` or the standalone rating list after saving; the ask is to return to whatever page the user rated from (club page, meeting, reading list). Since `get_success_url()` is already dynamic per-view, the cleanest fix is a `next` query param threaded through the rating forms/modals, falling back to the current behavior when absent — avoids bespoke logic per calling page.
- **Review the rating-from-meeting / rating-from-reading-list flow.** **[to-do]** Related to the above — currently there's no "rate this book" entry point directly on the meeting or reading-list-item partials at all; add one that carries the `next` param described above.
- **Table view toggle (book title vs. user name).** **[to-do]** `BookRatingListView`/`ClubBookRatingListView` already support filtering by `book_id`/`user_id`; this is mostly a template-level change — swap the primary column based on which filter is active.
- **Global and group average ratings.** **[to-do]** `Club.get_rated_books()` already annotates `avg_rating`/`n_ratings` per club; a "global average" (across all users) is a one-line addition (`Book.objects.annotate(avg_rating=Avg("ratings__rating"))`) — natural to surface on `BookDetailView`.

### Meeting creation enhancements
- ~~Separate date/time inputs~~, ~~add/select discussed books from reading lists~~ — **[to-do: done]**, confirmed implemented (`SplitDateTimeField`, `discussed_books` autocomplete scoped to the club).
- **Add locations logic — create a new location when creating a meeting.** **[to-do]** This is the most concrete gap found in review: `ClubMeetingForm.location` is restricted to `Location`s already linked via `ClubLocation`, but there is no UI anywhere to create that link (only via Django admin). Two things are needed: (a) a way to attach an existing `Location` to a club (simple `ClubLocation` create form/modal), and (b) optionally, an inline "create new location" affordance in the meeting form itself (e.g. a modal similar to the existing reading-list-item-add-book modal pattern already used elsewhere in the app).
- **Add online/in-person option.** **[to-do]** Needs a new field on `ClubMeeting` (e.g. `meeting_type` choice field, or make `location` nullable *and* add a `meeting_url`/`is_online` field) plus a small form/template change to show/hide the location field accordingly.
- **Add new book from the meeting form.** **[to-do]** The Google Books search modal pattern (`ReadingListItemAddBookView` + `add_reading_list_item_modal.html`) already solves this exact problem for reading lists; reusing that pattern (search → `create-from-search` API → add to a reading list → available for `discussed_books`) is more consistent than building a separate book-creation path inside the meeting form.

### Member invites
- **Email invite.** **[to-do]** No `ClubMembership`-creation UI exists at all today (see architecture doc — membership is only editable via the admin or the club's raw `members` multi-select). Before building email invites, there should be a normal "add member" flow with a token/invite model (`ClubInvite`: email, club, token, status, expiry) so invites work for people without an account yet. Requires configuring `EMAIL_BACKEND`/SMTP settings, which aren't present in `settings.py` currently.
- **Invitation QR code.** **[to-do]** Natural follow-on once invite tokens exist — a QR code encoding the invite-accept URL. Needs a QR-generation library (e.g. `qrcode`) added to dependencies.

### Personal club structure
- **Reuse full club structure for personal lists.** **[to-do]** `ReadingList.club` is already nullable, so personal (club-less) lists exist at the model layer today. The gap is UI: `reading_list_detail.html` and its partials would need to conditionally hide club-only sections (meetings, member roster) when `reading_list.club is None`, which is the next bullet.
- **Hide "club-like" elements for personal lists.** **[to-do]** Mostly template conditionals (`{% if reading_list.club %}`) plus double-checking the `ReadingListPartialDetailView`/`ReadingListItemRowView` permission logic (already branches on `club` vs `created_by`, so the access-control half of this is done — only the presentational half remains).

### Dashboard view
- **Modify the main user page.** **[to-do]** `userdashboard/dashboard.html` is currently a static Bootstrap starter mockup — the "Add Club" modal doesn't submit anywhere, and the Edit/Delete buttons on reading lists and ratings aren't wired to any view. This is less "enhance" and more "finish" — recommend rebuilding it against the data the view already provides (`clubs`, `reading_lists`, `book_ratings`) with working links, before layering in new content.
- **Include key features (upcoming meetings, reading list highlights, etc.).** **[to-do]** `Club.next_meeting()` already exists and is used on the club detail page — reuse it here to build an "upcoming meetings across your clubs" widget. Would need a small aggregation across the user's clubs (e.g. `ClubMeeting.objects.filter(club__in=user.clubs.all(), date__gte=now).order_by("date")[:5]`).

### Permissions review
- **[to-do, in progress]** Matches finding #3 in the architecture doc. Superseded by an actual plan in `docs/PERMISSIONS_DESIGN.md` — two branches: `feature/club-membership-template-views` (in progress) for a shared `ClubMemberRequiredMixin`/`ReadingListAccessRequiredMixin` across the template views, then `feature/club-membership-drf-api` for the DRF-side `IsClubMember`-style permission class. See that doc for the exact per-view gaps found (some views had no check at all — `ReadingListCreateView`/`UpdateView`/`DeleteView` weren't even login-gated).

### Other to-do items
- **Integrate Google Maps ("later").** **[to-do]** Explicitly deferred by you; noting that `Location` has no coordinate fields yet, so this would need a model change (`latitude`/`longitude` or a single `PointField` if PostGIS is acceptable) before a map can render anything.
- **"Contacts" logic — link users who share a club.** **[to-do]** No model changes strictly required to *derive* this (`CustomUser.objects.filter(clubs__in=user.clubs.all()).distinct()`), but if the intent is a persistent contacts/friends list (vs. a computed view), that implies a new model.
- **Add places for each user (?).** **[to-do]** Marked as uncertain in your own notes — worth a quick scoping conversation before building: is this "locations a user personally likes to host at" (a `Location.owner` or per-user `Location` visibility), or something else?
- **Add polls for next book.** **[to-do]** New feature, no existing model to build on. Sketch: `BookPoll` (club, reading_list or a set of candidate books, open/close dates) + `BookPollVote` (poll, user, book, unique per user/poll) — same shape as `ClubMembership`/`BookRating`'s unique-constraint pattern already used elsewhere in the codebase, so it'd fit the existing conventions well.

## 3. Not in `to_do.txt`, but worth considering

- ~~**Automated tests.**~~ **[done, 2026-08-07]** 64 tests added across all five apps — models, permission checks, and the fixed views from §1 (see `docs/JOURNAL.md` for the coverage table). Still open: no coverage yet for `ClubMeeting` CRUD views, `BookRating` delete flows, or most write paths on `ClubMeetingViewSet`/`LocationsViewSet`; and the suite currently runs against the real dev Postgres DB (~95s), so a faster dedicated test-DB setup is worth doing before it grows much further.
- **Password reset flow.** Signup/login/logout exist, but there's no "forgot password" flow — likely wanted before any real users are onboarded, and ties into the same email-sending setup needed for member invites, so worth planning together.
- **Styled error pages / permission-denied UX.** The membership checks currently return a bare `HttpResponseForbidden("You are not allowed to view this meeting.")` — plain text, no styling, no link back anywhere. Once permissions are consolidated (see above), a small `403.html` template would make these feel intentional rather than like an error state.
- **Clean up the starter-template navbar dropdown.** `templates/includes/navbar.html` has a leftover "Dropdown / Action / Another action" Bootstrap sample menu — either repurpose it (e.g. user account menu) or remove it.
- **`.sample_data/` review.** The root `.sample_data/` folder (Goodreads dumps, Amazon review archives, spreadsheets) looks like it's used to seed the `populate_*` management commands but isn't referenced by any committed script path checked during this review beyond `creating_books.py`. Worth confirming what's still load-bearing for seeding vs. what can be dropped, since some of these archives are large to keep in a repo long-term (consider `.gitignore`-ing raw source data and documenting the seeding steps instead, if not already ignored).

## Suggested sequencing

1. ~~Bugs in §1~~ — done.
2. **Next up:** finish the dashboard (§2 "Dashboard view") — it's the app's front door post-login and is currently non-functional.
3. Meeting locations + online/in-person (§2 "Meeting creation") — directly blocks a core workflow (scheduling a meeting with a real place).
4. Permissions consolidation (§2 "Permissions review") — do this *before* adding member invites/QR codes, since invites expand who can reach these views. Now has two concrete, test-documented targets to fix as part of it: the DRF API's missing object-level permissions, and the four views where anonymous users get a bare 403 instead of a login redirect (see `docs/ARCHITECTURE.md` §"Notable gaps" #3).
5. Member invites → personal club structure → ratings polish → polls, roughly in that order, since each mostly builds on state the previous one introduces.
