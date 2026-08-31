from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView

from clubs.mixins import ClubMemberRequiredMixin
from clubs.models import Club, ReadingList
from books.models import BookRating
from locations.models import Location

# Create your views here.


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "userdashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user-related data to the context
        user = self.request.user
        context["user"] = user

        # Fetch user's clubs (assuming a many-to-many through ClubMembership)
        context["clubs"] = user.clubs.all()

        # Personal reading lists only - club reading lists may show up here
        # later, but not yet (see docs/DASHBOARD_DESIGN.md non-goals).
        context["reading_lists"] = ReadingList.objects.filter(
            created_by=user, club__isnull=True
        )

        # Fetch user's rated books
        context["book_ratings"] = BookRating.objects.filter(user=user)

        # Locations the user created, plus their clubs' locations.
        context["locations"] = Location.objects.filter(created_by=user) | (
            Location.objects.filter(club_locations__club__in=user.clubs.all())
        )
        context["locations"] = context["locations"].distinct()

        return context


class UserDashboardClubPreviewView(ClubMemberRequiredMixin, DetailView):
    """Right-panel preview for the dashboard's "My Clubs" tab."""

    model = Club
    template_name = "userdashboard/partials/club_preview_panel.html"
    context_object_name = "club"

    def get_club(self):
        return self.get_object()


class UserDashboardRatingPreviewView(LoginRequiredMixin, DetailView):
    """Right-panel preview for the dashboard's "Ratings" tab.

    Scoped to the requesting user's own ratings via get_queryset() - a
    request for someone else's rating id simply won't find it (404),
    same pattern used for the DRF viewsets' object-level scoping.
    """

    model = BookRating
    template_name = "userdashboard/partials/rating_preview_panel.html"
    context_object_name = "book_rating"

    def get_queryset(self):
        return BookRating.objects.filter(user=self.request.user)


## User clubs


# TODO: deprecated - the dashboard's "My Clubs" tab (UserDashboardView +
# UserDashboardClubPreviewView) replaces this standalone page. Kept for now
# rather than removed outright; nothing links to it from the new dashboard.
class UserClubListView(LoginRequiredMixin, ListView):
    model = Club
    template_name = "userdashboard/user_club_list.html"
    # context_object_name = "clubs"

    def get_queryset(self):
        # Get clubs the user is a member of
        return self.request.user.clubs.all()
