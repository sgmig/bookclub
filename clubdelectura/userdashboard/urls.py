from django.urls import path

from django.contrib.auth.views import LogoutView

from userdashboard.views import (
    UserDashboardView,
    UserDashboardClubPreviewView,
    UserDashboardRatingPreviewView,
    UserClubListView,
)


# TEMPLATE URLS!
app_name = "user_dashboard"

urlpatterns = [
    path("dashboard/", UserDashboardView.as_view(), name="dashboard"),
    path(
        "dashboard/club/<int:pk>/",
        UserDashboardClubPreviewView.as_view(),
        name="club-preview",
    ),
    path(
        "dashboard/rating/<int:pk>/",
        UserDashboardRatingPreviewView.as_view(),
        name="rating-preview",
    ),
    path("my_clubs/", UserClubListView.as_view(), name="user_clubs"),
]
