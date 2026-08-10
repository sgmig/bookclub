from rest_framework.permissions import BasePermission

from clubs.models import Club, ReadingList


class IsClubMemberForMeeting(BasePermission):
    """Require the requesting user to belong to the meeting's club.

    Mirrors ClubMemberRequiredMixin (clubs/mixins.py) for the DRF layer.
    """

    message = "You are not a member of this club."

    def has_permission(self, request, view):
        if view.action != "create":
            # retrieve/update/partial_update/destroy are covered by
            # has_object_permission below; list is scoped via get_queryset.
            return True

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
    """Require club membership (club reading lists) or creatorship (personal ones).

    Mirrors ReadingListAccessRequiredMixin (clubs/mixins.py) for the DRF layer.
    """

    message = "You do not have access to this reading list."

    def has_permission(self, request, view):
        if view.action != "create":
            return True

        reading_list_id = request.data.get("reading_list")
        if not reading_list_id:
            return False
        try:
            reading_list = ReadingList.objects.get(pk=reading_list_id)
        except (ReadingList.DoesNotExist, ValueError, TypeError):
            return False
        return self._has_access(request.user, reading_list)

    def has_object_permission(self, request, view, obj):
        return self._has_access(request.user, obj.reading_list)

    @staticmethod
    def _has_access(user, reading_list):
        if reading_list.club:
            return user in reading_list.club.members.all()
        return reading_list.created_by == user
