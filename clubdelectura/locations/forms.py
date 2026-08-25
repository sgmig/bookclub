from django import forms

from locations.models import Location


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "description", "address", "access_details", "is_private"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "access_details": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "is_private": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
