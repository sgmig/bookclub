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


class IsStaffForModification(BasePermission):
    """Only staff can change or remove a shared Book.

    create/retrieve/list stay open to any authenticated user - Book has no
    owner/club concept to restrict update to otherwise, and create needs to
    stay open for the Google Books import flow.
    """

    message = "Only staff can modify or delete books."

    def has_permission(self, request, view):
        if view.action in ("update", "partial_update", "destroy"):
            return request.user.is_staff
        return True
