from django.urls import path

from django.contrib.auth.views import LogoutView

from accounts.views import CustomLoginView, ConfirmLogoutView, SignUpView


# TEMPLATE URLS!
app_name = "accounts"

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path(
        "logout_confirmation/", ConfirmLogoutView.as_view(), name="logout_confirmation"
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
