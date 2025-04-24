from django.shortcuts import render, redirect

from django.urls import reverse_lazy

from django.contrib.auth.views import LoginView

from django.views.generic import TemplateView, CreateView

from accounts.models import CustomUser
from accounts.forms import CustomUserCreationForm

# Create your views here.


class CustomLoginView(LoginView):

    template_name = "accounts/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("index")  # Redirect to home or dashboard
        return super().dispatch(request, *args, **kwargs)


class SignUpView(CreateView):

    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = "accounts/signup.html"  # Template to render the signup form
    success_url = reverse_lazy("index")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("index")  # Redirect to home or dashboard
        return super().dispatch(request, *args, **kwargs)


class ConfirmLogoutView(TemplateView):
    template_name = "accounts/logout.html"
