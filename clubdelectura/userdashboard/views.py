from django.shortcuts import render

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView

from clubs.models import Club, ReadingList
from books.models import BookRating

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

        context["reading_lists"] = ReadingList.objects.filter(created_by=user)

        # Fetch user's rated books
        context["book_ratings"] = BookRating.objects.filter(user=user)

        return context


## User clubs


class UserClubListView(LoginRequiredMixin, ListView):
    model = Club
    template_name = "userdashboard/user_club_list.html"
    # context_object_name = "clubs"

    def get_queryset(self):
        # Get clubs the user is a member of
        return self.request.user.clubs.all()
