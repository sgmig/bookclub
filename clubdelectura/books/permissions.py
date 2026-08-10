from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsRatingOwnerOrReadOnly(BasePermission):
    """Only the user who created a rating may update or delete it.

    Reads (list/retrieve) stay open - ratings are meant to be visible
    across a club, only mutation needs to be owner-restricted.
    """

    message = "You can only modify your own ratings."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user
