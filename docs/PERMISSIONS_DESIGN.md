# Plan: require club membership for club-scoped interactions

Three branches, in order:
1. `feature/club-membership-template-views` — Django template views. ✅ Done, merged 2026-08-07 (PR #2).
2. `feature/club-membership-drf-api` — DRF viewsets. ✅ Done, implemented 2026-08-10 — see "Phase 2" below for what actually shipped (a couple of things changed from the original sketch once written against the real code).
3. `fix/permissions-backlog-cleanup` — three items that accumulated in `docs/RECOMMENDATIONS.md` §"Permissions review" across Phase 2 and `feature/meeting-location-creation`. See "Phase 3" below.

This supersedes the "Permissions review" paragraph in `docs/RECOMMENDATIONS.md` §2 with an actual plan. It was also a prerequisite for `feature/meeting-location-creation` (parked, see `docs/LOCATIONS_DESIGN.md`) — that branch can now resume, since both the template views and the API it depends on enforce membership correctly.

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

## Phase 2 — implemented (`feature/club-membership-drf-api`)

### Mechanism

Two `permissions.BasePermission` subclasses in a new `clubs/permissions.py`, deliberately mirroring the Phase 1 mixins' club-lookup logic so the two don't drift:

```python
class IsClubMemberForMeeting(BasePermission):
    """Require the requesting user to belong to the meeting's club."""

    def has_permission(self, request, view):
        if view.action != "create":
            return True  # has_object_permission covers retrieve/update/destroy
        club_id = request.data.get("club")
        if not club_id:
            return False
        try:
            club = Club.objects.get(pk=club_id)
        except (Club.DoesNotExist, ValueError, TypeError):
            return False
        return request.user in club.members.all()

    def has_object_permission(self, request, view, obj):
        return request.user in obj.club.members.all()


class HasReadingListAccess(BasePermission):
    """Require club membership (club lists) or creatorship (personal lists)."""
    # same has_permission/has_object_permission shape, branching on
    # reading_list.club exactly like ReadingListAccessRequiredMixin
```

Applied as `permission_classes = [IsAuthenticated, IsClubMemberForMeeting]` / `[IsAuthenticated, HasReadingListAccess]` on `ClubMeetingViewSet` / `ReadingListItemViewSet` respectively.

**`get_queryset()` scoping, not just permission classes.** `has_permission`/`has_object_permission` alone don't stop `list` from enumerating other clubs' data — DRF permission classes gate individual actions, not what a queryset returns. So both viewsets' `get_queryset()` were also scoped: `ClubMeeting.objects.filter(club__members=request.user)` and the equivalent `Q(reading_list__club__members=user) | Q(reading_list__created_by=user)` for reading list items — regardless of any `club_id`/`reading_list_id` filter passed in, so passing someone else's id can't be used to peek at their data.

**Side effect worth knowing about**: because `retrieve`/`destroy` now use a queryset already scoped to accessible objects, a non-member's request to `/clubs/api/club-meeting/<id>/` (or the reading-list-item equivalent) returns **`404`, not `403`** — DRF's `get_object_or_404` never finds the row in the scoped queryset, so `has_object_permission` doesn't even get a chance to run. This is arguably *better* than `403` (it doesn't confirm to a non-member that the object exists at all), so kept as-is rather than working around it — but it does mean `403` and `404` are both "you can't see this" in this app now, worth remembering when reading logs/reports.

### Found while implementing (not in the original sketch)

1. **`BookRatingViewSet` had the same class of gap, but ownership-scoped, not club-scoped.** `permission_classes = [IsAuthenticated]` with no object-level check meant any authenticated user could `PATCH`/`PUT`/`DELETE` **any other user's** rating via `/books/api/book-rating/<id>/` — `perform_create` already forces `user=request.user` on create, but nothing stopped a different user from then editing or deleting it. Not part of the original Phase 2 sketch (which only covered club-scoped resources), but the same category of bug, small to fix, and directly analogous — so fixed here rather than deferred. Added `books/permissions.py::IsRatingOwnerOrReadOnly` (reads stay open — ratings are meant to be visible across a club; only mutation is owner-restricted) and applied it alongside `IsAuthenticated` on `BookRatingViewSet`.

2. **`ClubMeetingViewSet.create`/`update` were already broken, unrelated to permissions.** `ClubMeetingSerializer` nests `location` (`LocationSerializer()`) and `discussed_books` (`ReadingListItemSerializer(many=True)`) as writable-by-default nested serializers, with no `create()`/`update()` override on the serializer or the viewset. Confirmed empirically (see below) that `POST`/`PUT`/`PATCH` against this endpoint raises `AssertionError: The .create() method does not support writable nested fields by default` for any valid payload — this is a pre-existing serializer design issue, not something this branch introduced, and out of scope to fix here (fixing it properly means deciding on a create/update serializer split, mirroring the `ReadingListItemViewSet`/`BookRatingViewSet` Create-vs-Detail-serializer pattern already used elsewhere — a real follow-up worth doing, just not a "permissions" change). Because of this, `create`/`update` permission-*denial* is still fully tested (permission checks run before serializer validation, so non-member rejection is unaffected), but the "member is allowed to create" side of `create` is tested against `IsClubMemberForMeeting` directly rather than via a full POST, since a full POST can't succeed today regardless of who's making it.
   ```
   >>> ClubMeetingSerializer(data={...fully valid nested payload...}).save()
   AssertionError: The `.create()` method does not support writable nested fields by default.
   Write an explicit `.create()` method for serializer `clubs.serializers.ClubMeetingSerializer`,
   or set `read_only=True` on nested serializer fields.
   ```

### Deliberately not touched

- **`LocationsViewSet`** — still just `IsAuthenticated`, per the original plan: `Location` isn't club-scoped at the model level yet (that's what `feature/meeting-location-creation` adds via `ClubLocation`). Revisit permissions there once that branch resumes and actually has a club to check membership against.
- **`BookViewSet`** — any authenticated user can still `DELETE` any shared `Book` via the API (cascading to every rating and reading-list-item referencing it — both have `on_delete=CASCADE`). Found while auditing every `ModelViewSet` in the app for this work, but it's a different shape of problem than everything else here: `Book` has no owner/club concept at all (no `created_by`), so there's no natural "whose is it" check to add — the real question is a policy one ("should regular users be able to delete shared catalog entries at all, or should that be staff-only?"), not a missing-membership-check bug. Flagging for a decision rather than picking one unilaterally; not fixed in this branch.

### Testing

24 new tests across `clubs/tests.py` (`ReadingListItemAPIPermissionTests`, `ClubMeetingAPIPermissionTests`) and `books/tests.py` (`BookRatingViewSetOwnershipTests`) — 108 total, up from 85. Covers: create permission (member/non-member/creator/non-creator, plus anonymous), retrieve/destroy (member/non-member → 404 per the note above), and `list` queryset scoping (own data returned, other clubs'/users' data excluded even when explicitly requested via query params).

## Phase 3 — plan (`fix/permissions-backlog-cleanup`)

Three items accumulated in `docs/RECOMMENDATIONS.md` §"Permissions review" across Phase 2 and `feature/meeting-location-creation`. Bundling them into one branch since all three are small and in the same neighborhood of code.

### 1. Update/`partial_update` don't re-validate a *new* club/reading-list in the payload

**The gap**: `IsClubMember.has_permission` only inspects `request.data.get("club")` when `view.action == "create"`. For `update`/`partial_update`, it returns `True` unconditionally, and `has_object_permission` only checks the object's *existing* `.club` — never the new value being written. So a member of club A could `PATCH` an existing `ClubMeeting` or `ClubLocation` they belong to, setting `club` to club B, and nothing would stop it (they don't need to belong to club B). Same shape of gap in `HasReadingListAccess` for the `reading_list` field on `ReadingListItemViewSet`.

**Fix**: extend `has_permission` to run the same club-membership check for `update`/`partial_update` too, but only when the payload actually includes a `club` (or `reading_list`) key — if it's absent, nothing's being re-targeted, so `has_object_permission`'s existing-object check is sufficient on its own.

```python
class IsClubMember(BasePermission):
    def has_permission(self, request, view):
        if view.action not in ("create", "update", "partial_update"):
            return True
        club_id = request.data.get("club")
        if not club_id:
            # create requires a club; update/partial_update without one
            # just isn't re-targeting - has_object_permission covers it.
            return view.action != "create"
        return self._is_member(request.user, club_id)

    def has_object_permission(self, request, view, obj):
        return request.user in obj.club.members.all()

    @staticmethod
    def _is_member(user, club_id):
        try:
            club = Club.objects.get(pk=club_id)
        except (Club.DoesNotExist, ValueError, TypeError):
            return False
        return user in club.members.all()
```

Same restructuring for `HasReadingListAccess`, keyed on `reading_list` instead of `club`, reusing its existing `_has_access` staticmethod. Covers `ClubMeetingViewSet`, `ClubLocationViewSet` (both via `IsClubMember`), and `ReadingListItemViewSet` (via `HasReadingListAccess`) with one change each.

**Tests to add**: member can't `PATCH` `club`/`reading_list` on an object they own to a club/list they don't belong to (for all three viewsets); member *can* still `PATCH` unrelated fields without re-sending `club`/`reading_list`; existing create-permission tests should be unaffected (behavior there doesn't change).

### 2. `ClubMeetingSerializer` create/update crash (the actual bug, not just a permissions gap)

**The bug**: `ClubMeetingSerializer` nests `location` (`LocationSerializer()`) and `discussed_books` (`ReadingListItemSerializer(many=True)`) as writable-by-default, with no `create()`/`update()` override — confirmed empirically in Phase 2 that any valid `POST`/`PUT`/`PATCH` against `/clubs/api/club-meeting/` raises `AssertionError: The .create() method does not support writable nested fields by default`. `ClubMeetingViewSet` has never had a working create or update via the API.

**Fix**: the same Create/Detail serializer split already used by `ReadingListItemViewSet`/`BookRatingViewSet`/`ClubLocationViewSet`:

```python
class ClubMeetingCreateSerializer(serializers.ModelSerializer):
    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all())
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, allow_null=True
    )
    discussed_books = serializers.PrimaryKeyRelatedField(
        queryset=ReadingListItem.objects.all(), many=True, required=False
    )

    class Meta:
        model = ClubMeeting
        fields = ["club", "date", "location", "discussed_books", "notes"]
```

`ClubMeetingViewSet.get_serializer_class()` routes `create`/`update`/`partial_update` to `ClubMeetingCreateSerializer` and `retrieve`/`list` to the existing `ClubMeetingSerializer` (nested, read-only in practice now that nothing writes through it) — going one step further than the `ReadingListItemViewSet`/`BookRatingViewSet` precedent, which only branches on `create` and leaves `update` on the nested Detail serializer. Worth doing here since fixing `update` too costs nothing extra once the Create serializer exists.

`create()` override re-serializes the response with the Detail serializer for the rich nested output, matching the existing pattern.

**Found while writing this plan, not part of this fix**: `BookRatingSerializer`/`ReadingListItemSerializer` have the identical latent issue for a full `PUT` (not `PATCH`) — their `get_serializer_class()` only special-cases `create`, so `update`/`partial_update` fall through to the nested Detail serializer. A `PATCH` with only non-nested fields (e.g. `{"rating": 9}`) works fine — which is all that's tested and all the app's own JS ever sends — but a full `PUT` including the nested field would crash the same way. Not touched here (nothing in the app sends a full `PUT` to either endpoint today, and it's outside the three items actually on the backlog) — flagging for the backlog rather than expanding this branch's scope.

**Tests to add**: successful `create` via the API (previously impossible to test at all — permission-denial was tested, but "member succeeds" never was); successful `update`/`partial_update`; existing permission tests should keep passing unchanged.

### 3. `Book` deletion policy — ✅ confirmed 2026-08-30

**The gap**: `BookViewSet` only checks `IsAuthenticated`. Any authenticated user can `DELETE` (or, as discussed, `UPDATE`) any shared `Book`, cascading to every `BookRating`/`ReadingListItem` referencing it (both `on_delete=CASCADE`). `Book` has no owner/club concept at all — this isn't a missing-membership-check bug like the others, it's a policy question.

**Confirmed**: staff-only for both `update`/`partial_update` and `destroy`; `create`/`retrieve`/`list` stay open to any authenticated user (`create` needs to, for the Google Books import flow to keep working). New `books/permissions.py::IsStaffForModification`:

```python
class IsStaffForModification(BasePermission):
    """Only staff can change or remove a shared Book.

    create/retrieve/list stay open to any authenticated user - Book has no
    owner/club concept to restrict update to otherwise, and create needs to
    stay open for the Google Books import flow.
    """

    def has_permission(self, request, view):
        if view.action in ("update", "partial_update", "destroy"):
            return request.user.is_staff
        return True
```

Applied alongside `IsAuthenticated` on `BookViewSet`.

**Tests to add**: staff can update/delete a `Book`; non-staff authenticated user gets `403` for both; `create`/`retrieve`/`list` unaffected for regular users.

### Not in this plan

- The `BookRatingSerializer`/`ReadingListItemSerializer` full-`PUT` latent bug noted above (§2) — same shape as the fixed `ClubMeetingSerializer` bug, but nothing currently exercises it.
- Any further hardening of `BookViewSet.update` — only `destroy` is addressed per the backlog note; `update` wasn't flagged as a problem.
