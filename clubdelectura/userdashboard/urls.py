from django.urls import path

from django.contrib.auth.views import LogoutView

from userdashboard.views import UserDashboardView, UserClubListView


# TEMPLATE URLS!
app_name = "user_dashboard"

urlpatterns = [
    path("dashboard/", UserDashboardView.as_view(), name="dashboard"),
    path("my_clubs/", UserClubListView.as_view(), name="user_clubs"),
]
