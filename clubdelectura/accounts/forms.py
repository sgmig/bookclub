from django import forms
from django.db import models
from django.contrib import admin
from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
    BaseUserCreationForm,
    SetUnusablePasswordMixin,
)
from django.core.exceptions import ValidationError

from accounts.models import CustomUser


class CustomUserCreationForm(BaseUserCreationForm):
    """Define a new user creation form that does not include username.
    In this case we're fine just inheriting from BaseUserCreationForm and just pointing the meta to the new model.
    """

    class Meta(BaseUserCreationForm.Meta):
        model = CustomUser  # Ensure this points to your custom user model
        fields = ("email", "first_name", "last_name")  # Add the desired fields


class AdminCustomUserCreationForm(SetUnusablePasswordMixin, CustomUserCreationForm):

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name")

    usable_password = SetUnusablePasswordMixin.create_usable_password_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False


class CustomUserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
        ]
