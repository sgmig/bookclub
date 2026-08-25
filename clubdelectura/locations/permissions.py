from rest_framework.permissions import BasePermission

from clubs.models import Club


class IsClubMemberForLocationCreate(BasePermission):
    """If a `club` is given on create, require the user to belong to it.

    Mirrors clubs/permissions.py::IsClubMemberForMeeting. Only has_permission
    is meaningful here: Location has no direct club to check on
    retrieve/update/destroy (the club link is a separate ClubLocation row),
    and this branch doesn't add any UI for editing/deleting locations, so
    those actions are left exactly as they were - IsAuthenticated only.
    """

    message = "You are not a member of this club."

    def has_permission(self, request, view):
        if view.action != "create":
            return True

        club_id = request.data.get("club")
        if not club_id:
            # Creating a location with no club is allowed (e.g. a future
            # "add a location" flow outside a specific club's meeting form).
            return True
        try:
            club = Club.objects.get(pk=club_id)
        except (Club.DoesNotExist, ValueError, TypeError):
            return False
        return request.user in club.members.all()
