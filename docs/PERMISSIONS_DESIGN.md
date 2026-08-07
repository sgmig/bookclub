# Plan: require club membership for club-scoped interactions

Two branches, in order:
1. `feature/club-membership-template-views` — Django template views (this doc's main focus).
2. `feature/club-membership-drf-api` — DRF viewsets (`ReadingListItemViewSet`, `ClubMeetingViewSet`, and whatever the locations feature adds later). Sketched at a lighter level here; will get its own detailed pass when that branch starts.

This supersedes the "Permissions review" paragraph in `docs/RECOMMENDATIONS.md` §2 with an actual plan. It's also a prerequisite for `feature/meeting-location-creation` (parked, see `docs/LOCATIONS_DESIGN.md`) — that branch's "add location" flow reads correctly once the meeting-creation view it lives on actually enforces membership itself.

## Current state — exact, verified against `clubs/views.py`

| View | Today | Gap |
|---|---|---|
| `ClubUpdateView` | `LoginRequiredMixin` only | Any logged-in user can edit *any* club, not just ones they're in |
| `ClubDeleteView` | `LoginRequiredMixin` only | Same — any logged-in user can delete *any* club |
| `ClubMeetingCreateView` | `LoginRequiredMixin` only | Any logged-in user can create a meeting for *any* club (the gap that started this conversation) |
| `ClubMeetingUpdateView` | `LoginRequiredMixin` only | Same, for editing an existing meeting |
| `ClubMeetingDeleteView` | `LoginRequiredMixin` only | Same, for deleting one |
| `ReadingListCreateView` | **Nothing** — no `LoginRequiredMixin` at all | See "bug found" below — this one's worse than a missing permission check |
| `ReadingListUpdateView` | **Nothing** | Any logged-in user can edit *any* reading list, club or personal, theirs or not |
| `ReadingListDeleteView` | **Nothing** | Same, for deleting one |
| `ClubMeetingDetailView` / `ClubMeetingPartialDetailView` | Hand-rolled `dispatch()` membership check | Correct outcome, but see "known UX bug" below |
| `ReadingListPartialDetailView` / `ReadingListItemRowView` | Hand-rolled `dispatch()` club-or-creator check | Same |
| `ClubBookRatingListView` | Hand-rolled `dispatch()` membership check (fixed in `fix/small-bugs-and-tests` — it used to be dead code) | Same UX bug as above, not fixed last time |

**Bug found while reading this code (not just a missing check): `ReadingListCreateView` crashes for anonymous users.** Its `get_form_kwargs()` unconditionally passes `user=self.request.user` to `ReadingListForm`, which does `self.fields["club"].queryset = user.clubs.all()` whenever `user` is truthy — and `AnonymousUser` *is* truthy (it's just an object), but has no `.clubs` attribute (that's only defined on the real `CustomUser` model via the M2M's `related_name`). Result: any anonymous request to the reading-list-create page — not even a POST, the initial `GET` — raises an unhandled `AttributeError` (500). Same category of bug as `BookRatingCreateView`/`BookRatingModalView` fixed in the previous branch (custom logic touching `request.user` before any login check has run). This gets fixed as a side effect of adding `LoginRequiredMixin` here — flagging it explicitly since it's a genuine crash, not just a hardening.

**Known UX bug, already documented in `docs/ARCHITECTURE.md` #3 and deliberately deferred there**: the four "hand-rolled `dispatch()`" rows above run their membership check *before* calling `super().dispatch()`, so `LoginRequiredMixin`'s login-redirect never gets a chance to fire for anonymous users — they get a bare `403` instead. Not fixed at the time because fixing it meant touching several views at once, which is exactly what this branch is already doing — so it gets fixed here as a natural side effect of moving these four onto the same shared mixin as everything else, rather than as separate work.

**Also confirmed *not* a bug, so not touched**: `ReadingListForm`'s club dropdown is already safely scoped — when a `club_id` is passed in, the field is `disabled`, and Django ignores POST data for disabled fields (uses `initial` instead); when no `club_id` is passed, the queryset is restricted to `user.clubs.all()`, and Django's `ModelChoiceField` rejects any submitted value outside that queryset. So a non-member can't get a reading list attached to a club they don't belong to by tampering with the POST body, even before this branch's fix. `ReadingListCreateView` needs `LoginRequiredMixin` (for the crash) but not a bespoke club-membership check on top — the form already enforces it correctly.

## Proposed mechanism

Two small mixins in a new `clubs/mixins.py`, both `LoginRequiredMixin` subclasses that check authentication explicitly *before* doing any DB lookup keyed on `request.user` (this is precisely what the "known UX bug" above and the earlier `BookRatingCreateView` crash both got wrong — check login first, always):

```python
class ClubMemberRequiredMixin(LoginRequiredMixin):
    """Require the user to belong to self.get_club()."""

    def get_club(self):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        club = self.get_club()
        if request.user not in club.members.all():
            raise PermissionDenied("You are not a member of this club.")
        return super().dispatch(request, *args, **kwargs)


class ReadingListAccessRequiredMixin(LoginRequiredMixin):
    """Require club membership (club lists) or creatorship (personal lists)."""

    def get_reading_list(self):
        return self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        reading_list = self.get_reading_list()
        if reading_list.club:
            if request.user not in reading_list.club.members.all():
                raise PermissionDenied("You are not a member of this club.")
        elif reading_list.created_by != request.user:
            raise PermissionDenied("You are not the creator of this reading list.")
        return super().dispatch(request, *args, **kwargs)
```

Using `django.core.exceptions.PermissionDenied` instead of the existing ad hoc `return HttpResponseForbidden("...")` pattern — Django's default exception handling turns it into a real `403` response, and if a `403.html` template is ever added (already on the list in `docs/RECOMMENDATIONS.md` §3 "Styled error pages"), every view using these mixins gets it for free, with no further changes. This is a deliberate small upgrade over the current per-view bespoke-message convention, not just a mechanical refactor — flagging in case you'd rather keep matching the existing style.

**Per-view wiring** (`get_club()` / `get_reading_list()` implementations):

| View | Accessor |
|---|---|
| `ClubUpdateView`, `ClubDeleteView` | `get_club(self): return self.get_object()` |
| `ClubMeetingCreateView` | `get_club(self): return get_object_or_404(Club, id=self.kwargs["club_id"])` |
| `ClubMeetingUpdateView`, `ClubMeetingDeleteView`, `ClubMeetingDetailView`, `ClubMeetingPartialDetailView` | `get_club(self): return self.get_object().club` |
| `ClubBookRatingListView` | `get_club(self): return get_object_or_404(Club, id=self.kwargs["club_id"])` (already fetches this in its own `get_queryset`; consolidates onto the shared mixin instead of its own hand-rolled `dispatch()`) |
| `ReadingListUpdateView`, `ReadingListDeleteView`, `ReadingListPartialDetailView` | default `get_reading_list()` (`self.get_object()`) — no override needed |
| `ReadingListItemRowView` | `get_reading_list(self): return self.get_object().reading_list` |
| `ReadingListCreateView` | Just `LoginRequiredMixin` (fixes the crash) — no membership mixin needed, per the "already safe" note above |

**Not touched**: `ClubCreateView` (no club exists yet — nothing to check membership against), `ClubListView`/`ClubDetailView` (already `LoginRequiredMixin`, and being read-only + not scoped to "your" clubs specifically, membership-gating them wasn't part of what you asked for — flagging in case you want that too, but treating it as out of scope unless you say otherwise), `ReadingListDetailView` (already `LoginRequiredMixin`, and — unlike its partial-view sibling — never had a membership check even before this plan; **candidate for the same `ReadingListAccessRequiredMixin`, listing it here for a decision rather than silently changing it, since tightening a "logged in" page to "club members only" is a behavior change worth confirming**).

**Known accepted inefficiency**: `get_club()`/`get_reading_list()` call `self.get_object()`, and the underlying `UpdateView`/`DeleteView` call it again themselves — one extra DB query per request. Not worth the complexity of caching across the mixin boundary for views this low-traffic.

## Permission scope decisions (defaulting, flag if wrong)

- **Any club member**, not just admins, can update/delete a club, create/update/delete meetings, and manage reading lists — consistent with the app's existing granularity everywhere else (`ClubMembership.is_admin` exists but is enforced nowhere in the app today; introducing the first admin-only gate is a bigger policy decision than "require membership," so not bundling it in here).
- `ReadingListDetailView` — listed above as an open call, not yet decided.

## Testing plan

Extend `clubs/tests.py`: for every view in the table above, cover (a) member → allowed, (b) non-member → `403`, (c) anonymous → redirect to login (not `403` — this is the regression test for the UX bug fix), (d) for `ReadingListCreateView` specifically, anonymous → redirect (regression test for the crash fix, replacing a 500 with a 302).

## Phase 2 (separate branch, sketch only)

DRF viewsets currently only check `IsAuthenticated`, with no per-object check:
- `ReadingListItemViewSet` — `create`/`update`/`delete` should require membership in the item's reading list's club (or creatorship, for personal lists — same branching as above).
- `ClubMeetingViewSet` — `create`/`update`/`delete` should require membership in the meeting's club; `list` accepts a `club_id` filter today with no check that the requester belongs to that club.
- Whatever `LocationsViewSet` looks like once `feature/meeting-location-creation` resumes (that design already commits to checking membership on its new club-scoped creation endpoint).

Proposed shape: a `permissions.BasePermission` subclass (`IsClubMemberOrReadOnly`, or split into has-permission/has-object-permission checks per DRF convention), mirroring the same club-lookup logic as the template-view mixins above so the two don't drift. Full design deferred to when that branch starts, per your instruction to sequence this after the template-view pass.
