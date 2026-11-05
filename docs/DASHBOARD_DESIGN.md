# Design: rebuild the user dashboard on the club page's structure

Branch: `feature/user-dashboard`. Design-only — no code changes yet.

## The ask

From the conversation that kicked this off: rebuild `userdashboard/dashboard.html` (currently a static, non-functional Bootstrap mockup) around the same look and structure as the club detail page, so the two feel like one consistent app rather than two different UIs bolted together. Four tabs:

1. **"My Clubs"** (replaces "Members" as the first/main tab) — left panel lists the clubs the user belongs to; clicking one shows, on the right: the club's name, description, and its *next* meeting only (same format as the club page's meeting detail, not a full meeting list) — or a "no upcoming meetings" message if there isn't one. A "Go to club page" button in the top-right of the right panel.
2. **"Reading Lists"** — the user's own *personal* reading lists (`club=None`), not club ones. Room to add club reading lists here later, but not now.
3. **"Ratings"** — the user's own ratings.
4. **"Locations"** — already on the backlog from `docs/LOCATIONS_DESIGN.md`: locations the user created, plus their clubs' locations.

Page header becomes "Welcome, {{ user.first_name }}" instead of a club name — otherwise the layout (tabs, left-list/right-detail panels) mirrors `club_detail.html` directly.

## The design question: personal-club structure, or a dedicated dashboard?

You asked for a real opinion here, not just a pros/cons list, so: **build a dedicated dashboard. Don't model a user's personal space as a `Club`.**

The case for the personal-club route is real — `ClubDetailView`, `ClubMembership`, the meeting/reading-list/rating infrastructure all already work, and reusing them outright would be less code today. But it buys that speed by making `Club` mean two different things (a real multi-person club, and a stand-in for "this one user's stuff"), and that seam doesn't stay free:

- **Every future club-only feature needs a personal-club exception, forever.** Email invites, QR invites, admin roles, club deletion/transfer, anything about multiple members — each one needs an `if club.is_personal: skip/hide this` somewhere, scattered across whichever view happens to touch it. That's exactly the kind of accreting special-case debt that's expensive to find and easy to get wrong later, not a one-time cost.
- **The permission model stops meaning what it says.** `IsClubMember`/`ClubMemberRequiredMixin` and `ClubMembership` currently mean "this person is one of possibly-several members of a real club." A personal club needs exactly one member — themselves — forever, which is a new invariant every membership-management code path (including the existing raw `members` multi-select on `ClubForm`) would need to respect, or you risk someone's "personal club" quietly gaining a second member through a code path that was never taught the concept exists.
- **It fights the grain of what's already built.** Personal reading lists (`club=None`) already exist and work today, with their own tested permission branch (`ReadingListAccessRequiredMixin`: club membership *or* creator, depending on whether `club` is set). That dual-mode design is already the "personal vs. club" answer this codebase settled on elsewhere — retrofitting a personal-club model here would mean either migrating existing personal lists onto synthetic per-user clubs, or running two different representations of "this is personal" side by side.
- You said it yourself, and I think it's the right instinct: *"conceptually a club and a user are different, and in the future they might share less features."* That's precisely the situation where taking the shortcut costs more than it saves — the whole value of the shortcut is that the two things stay similar, and you're already expecting them not to.

**The actual thing you want — visual and structural consistency — doesn't require sharing the data model.** `club_detail.html`'s tab shell, its list-on-the-left/detail-on-the-right convention, and several of its partials are already generic enough to reuse directly against dashboard-shaped data:

- `clubs/partials/club_meeting_detail_panel.html` — the exact "next meeting" format you asked for — can be `{% include %}`'d as-is for the dashboard's club preview.
- `clubs/partials/reading_list_detail_panel.html`, and the view/URL behind it (`ReadingListPartialDetailView` / `clubs:reading-list-detail-panel`), already handle personal (`club=None`) reading lists correctly — the permission check already branches on creator vs. club membership. The dashboard's Reading Lists tab can point at this exact URL for its right panel with no changes.
- The tab-shell JS (`clubs/static/clubs/js/club_detail.js` — activate a tab from the URL hash) is generic; the click-to-load-a-panel JS pattern (`club_meeting.js`, `reading_list/dynamic_init.js`) is copy-once-adapt, not copy-and-diverge.

So: same look, same feel, most of the interaction code reused wherever the data shape actually matches — but `Club` keeps meaning one thing, and nothing about a user's personal space needs to pretend to be a club with one member.

## Current state (baseline)

- `userdashboard/views.py::UserDashboardView` — context already provides `clubs` (`user.clubs.all()`), `reading_lists` (**all** of the user's reading lists today, not filtered to personal ones), and `book_ratings`. Needs updating: reading lists should filter to `club__isnull=True`.
- `userdashboard/templates/userdashboard/dashboard.html` — fully static mockup, being replaced entirely. The "Add Club" modal doesn't submit anywhere; Edit/Delete buttons on reading lists and ratings aren't wired to anything; the one working link (club "Edit") actually points at club *detail*, not edit.
- `userdashboard/views.py::UserClubListView` (`readers/my_clubs/`) — a separate full-page club list, linked from the old mockup's "My book clubs" button. Once the new dashboard's "My Clubs" tab exists, this becomes redundant — proposing to remove it rather than leave unreferenced dead code (nothing else links to it).
- No locations template exists anywhere yet — the locations feature (`docs/LOCATIONS_DESIGN.md`) built the create-modal flow but explicitly deferred the "view your locations" UI to this dashboard work.

## Proposed structure

Same shell as `club_detail.html`: `<h1>`/header, Bootstrap `nav-tabs`, `tab-content` panes, each pane following the left-list/right-detail convention where the tab needs one.

### Tab 1: My Clubs

- Left panel: `user.clubs.all()`, one `list-group-item` per club (name + member count, say), each with `data-club-preview-url="{% url 'user_dashboard:club-preview' club.id %}"`.
- Right panel (loaded via fetch on click, same mechanic as `club_meeting.js`'s `loadMeetingDetails`): a new partial, `userdashboard/partials/club_preview_panel.html` —
  - Club name (`<h3>`) + description.
  - `{% include "clubs/partials/club_meeting_detail_panel.html" with club_meeting=club.next_meeting %}` if `club.next_meeting` exists, else a "No upcoming meetings" message.
  - "Go to club page" button, top-right, linking to `clubs:club-detail`.
- Backing view: `UserDashboardClubPreviewView(ClubMemberRequiredMixin, DetailView)` on `Club`, reusing `ClubMemberRequiredMixin` directly (same import `userdashboard` already relies on `clubs`/`books` models for, so no new dependency-direction concern like the one caught in the locations work) — this is what stops a user from previewing a club they don't belong to by guessing an id.

### Tab 2: Reading Lists

- Left panel: `ReadingList.objects.filter(created_by=user, club__isnull=True)`.
- Right panel: reuses `clubs:reading-list-detail-panel` (`ReadingListPartialDetailView` + `reading_list_detail_panel.html`) unmodified — already permission-checked for personal lists, already has working Add Book / Edit / Delete.
- "New reading list" button: `clubs:reading-list-create` with no `club_id` param (already produces a personal list today — this path exists and works, just isn't exposed anywhere with real navigation to it currently).

### Tab 3: Ratings

- `BookRating.objects.filter(user=user)`.
- The existing ratings-row partial (`books/partials/book_rating_row.html`) shows *user* as the identifying column, because it's built for "one book, many raters" (the club ratings tab's shape). Here it's the reverse — one user, many books — so this needs a small variant with book title as the identifying column instead of user. Same edit/delete buttons/modals underneath (`book-rating-modal`, `book-rating-delete-modal`) work unchanged, since they're already keyed off the rating id, not the row's display column.
- This is effectively the first real use case for the "table view toggle" item already sitting in `docs/RECOMMENDATIONS.md` §"Book ratings views" — worth a one-line cross-reference when this lands rather than treating it as a coincidence.

### Tab 4: Locations

- `Location.objects.filter(created_by=user)` (created by you) unioned with `Location.objects.filter(club_locations__club__in=user.clubs.all())` (your clubs' locations) — both querysets already used verbatim in `docs/RECOMMENDATIONS.md`'s note on this deferred item.
- Display-only for now: name, address (or "— redacted —" if blank on a private location), which club(s) it's linked to. No create/edit here — creation already happens via the meeting-form modal; nothing in the ask requires more than viewing for this pass.

## What's new vs. reused

| Piece | New or reused |
|---|---|
| Tab shell, header, layout | New markup, but copying `club_detail.html`'s structure directly |
| Tab-activate-from-hash JS | Reused pattern (`club_detail.js` is generic; copy into `userdashboard/static/userdashboard/js/`) |
| My Clubs → club preview | New view + partial + JS click-handler, modeled on `club_meeting.js`'s fetch-and-inject shape |
| My Clubs → next meeting display | Fully reused: `{% include %}` of `club_meeting_detail_panel.html` |
| Reading Lists tab right panel | Fully reused: existing URL, view, and partial, unmodified |
| Ratings tab | New partial (row variant) + new queryset; existing modals/buttons reused underneath |
| Locations tab | New partial + new queryset; first template this app has ever needed |

## Open questions

1. **Remove `UserClubListView`/`readers/my_clubs/`, or leave it?** Nothing will link to it anymore once this ships. I'd remove it rather than leave dead code, but it's your call if you want it kept as a standalone page for some other reason.
2. **"My Clubs" left-panel content** — just the club name, or name + something else (member count, next meeting date as a preview without clicking in)? Proposing just the name for a first pass, matching how the other three tabs' left panels are similarly minimal (title-only list items) — easy to enrich later.
3. **Ratings tab — flat list, or keep the left/right split for consistency?** Proposing a flat table (no click-through needed, edit/delete happens inline via the existing modals) since there's no natural "detail view" beyond what the row already shows — unlike meetings/reading-lists, a rating doesn't have more detail to reveal on click. Flagging since the other three tabs all use the split pattern and this one wouldn't.

## Non-goals for this branch

- Club reading lists on the Reading Lists tab (explicitly deferred by you — "maybe we'll add that later, maybe not").
- Any editing/creation UI on the Locations tab beyond what already exists (the meeting-form modal).
- The "table view toggle" backlog item itself (book-title vs. user-name columns as a *general*, reusable switch) — this branch only builds the one new variant it needs for the Ratings tab, not a generalized toggle.
- Removing the underlying `club=None` reading-list data model in favor of anything club-shaped — per the design decision above, personal stays personal.

## Implementation notes

Open questions were resolved as follows, each a deviation from my original proposal:

1. **`UserClubListView` kept, not removed.** Marked with a `# TODO: deprecated` comment pointing at the new "My Clubs" tab as its replacement. Nothing links to it from the new dashboard, but it stays reachable at `readers/my_clubs/` and its tests are unchanged.
2. **My Clubs left panel shows member count**: `{{ club.name }} - {{ club.members.count }} member{{ club.members.count|pluralize }}`, not name-only.
3. **Ratings tab kept the left/right split** (not the flat table I'd proposed), for consistency with the other three tabs: left panel lists `{{ book.title }} - {{ rating }}`, right panel (`rating_preview_panel.html`) shows title, rating, comment, and an Edit button that opens the existing book-rating modal.

What shipped, roughly matching the original plan otherwise:

- `UserDashboardView` now filters `reading_lists` to `club__isnull=True` and unions `Location.objects.filter(created_by=user)` with `Location.objects.filter(club_locations__club__in=user.clubs.all())`, deduplicated with `.distinct()`.
- `UserDashboardClubPreviewView` (`ClubMemberRequiredMixin` + `DetailView`) and `UserDashboardRatingPreviewView` (ownership-scoped queryset, so a non-owner gets a 404 rather than a 403) back the two click-through panels.
- The Reading Lists tab's right panel is the unmodified `clubs:reading-list-detail-panel` URL/view/partial, exactly as planned — zero new backend code for that tab.
- `userdashboard/static/userdashboard/js/dashboard.js` follows the established fetch-and-inject panel pattern, and reuses `bindBookRatingModalButtons` from `books/js/book_rating_list/book_rating_list_buttons.js` (imported as an ES module) to rewire the Edit button each time the rating panel reloads, rather than duplicating that logic.
- The Ratings tab's left-panel links carry both a `rating-preview-link` class (this dashboard's own click handler) and a `book-rating-link` class with `data-book-id` (unused by any dashboard code — present only so the *existing*, unmodified `refreshBookRatingList()` in the shared button-binding file can find and re-click this link after a successful modal edit, without that shared file needing to know the dashboard exists).
- Tests: `userdashboard/tests.py` grew from the original club-list-only coverage to include `UserDashboardViewTests` (context scoping, reading-list/location filtering), `UserDashboardClubPreviewViewTests` (member/non-member/anonymous/upcoming-vs-no-meeting), and `UserDashboardRatingPreviewViewTests` (owner/non-owner-404/anonymous). Full suite: 147 tests, all passing.

Bug found during browser verification (Playwright, headless Chromium): the Ratings tab template originally explained the `book-rating-link`/`data-book-id` reuse trick with a `{# ... #}` Django comment spanning multiple lines. Django's single-line comment tag doesn't support multi-line content — it rendered as literal visible text above the ratings list in the browser. Fixed by switching to `{% comment %}...{% endcomment %}` block syntax; re-verified via screenshot afterward, and grepped the rest of the new templates to confirm no other instance of the same mistake.

### Follow-up: "Create new club" button on the My Clubs tab

Added a "Create new club" button under the club list, linking to `clubs:club-create` — same placement/style as the "New reading list" button on the Reading Lists tab.

This surfaced a pre-existing inconsistency: `ClubCreateView.success_url` redirected to `clubs:club-list` (the browse-all-clubs page, not filtered to the user's own clubs) after creating a club. Changed it to `get_success_url` returning the new club's own detail page instead — consistent with `ReadingListCreateView`, which already redirects to the new list's detail page rather than back to a hub, and the more useful landing spot after creating something you're about to set up (invite members, plan a meeting) rather than bouncing back to a list. `ClubUpdateView`/`ClubDeleteView` were left pointing at `club-list`, since that's still the right place to land after editing or removing a club you're not about to look at further.

Updated `test_create_club_redirects_to_club_list` → `test_create_club_redirects_to_club_detail` in `clubs/tests.py` to match. Browser-verified end to end: clicked the new button from the dashboard, filled out the form, submitted, landed on the new club's detail page.
