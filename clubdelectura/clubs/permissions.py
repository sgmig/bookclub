from rest_framework.permissions import BasePermission

from clubs.models import Club, ReadingList


class IsClubMember(BasePermission):
    """Require the requesting user to belong to the object's club.

    Works for any model exposing a direct `club` FK/field - ClubMeeting and
    ClubLocation both do. Mirrors ClubMemberRequiredMixin (clubs/mixins.py)
    for the DRF layer.
    """

    message = "You are not a member of this club."

    def has_permission(self, request, view):
        if view.action not in ("create", "update", "partial_update"):
            # retrieve/destroy are covered by has_object_permission below;
            # list is scoped via get_queryset.
            return True

        club_id = request.data.get("club")
        if not club_id:
            # create always requires a club; update/partial_update without
            # one isn't re-targeting the object's club, so
            # has_object_permission's check against the existing club is
            # sufficient on its own.
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


class HasReadingListAccess(BasePermission):
    """Require club membership (club reading lists) or creatorship (personal ones).

    Mirrors ReadingListAccessRequiredMixin (clubs/mixins.py) for the DRF layer.
    """

    message = "You do not have access to this reading list."

    def has_permission(self, request, view):
        if view.action not in ("create", "update", "partial_update"):
            return True

        reading_list_id = request.data.get("reading_list")
        if not reading_list_id:
            # Same reasoning as IsClubMember above: create always needs a
            # reading_list; update/partial_update without one isn't
            # re-targeting, so has_object_permission covers it.
            return view.action != "create"
        return self._has_access_to_id(request.user, reading_list_id)

    def has_object_permission(self, request, view, obj):
        return self._has_access(request.user, obj.reading_list)

    @classmethod
    def _has_access_to_id(cls, user, reading_list_id):
        try:
            reading_list = ReadingList.objects.get(pk=reading_list_id)
        except (ReadingList.DoesNotExist, ValueError, TypeError):
            return False
        return cls._has_access(user, reading_list)

    @staticmethod
    def _has_access(user, reading_list):
        if reading_list.club:
            return user in reading_list.club.members.all()
        return reading_list.created_by == user
