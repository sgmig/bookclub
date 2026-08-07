from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class ClubMemberRequiredMixin(LoginRequiredMixin):
    """Require the logged-in user to belong to self.get_club()."""

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
    """Require club membership (club reading lists) or creatorship (personal ones)."""

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
