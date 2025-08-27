from django import forms
from django.utils import timezone

from locations.models import Location

from clubs.models import Club, ClubMeeting, ClubLocation, ReadingList, ReadingListItem


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ["name", "description", "members"]  # Add relevant fields

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "members": forms.SelectMultiple(attrs={"class": "form-control"}),
        }


class ReadingListForm(forms.ModelForm):

    class Meta:
        model = ReadingList
        fields = ["name", "club"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "club": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        club = kwargs.pop("club", None)
        super().__init__(*args, **kwargs)

        if club:
            self.fields["club"].initial = club
            self.fields["club"].disabled = True
        elif user:
            # Filter clubs where the user is a member
            self.fields["club"].queryset = user.clubs.all()
        else:
            self.fields["club"].queryset = self.fields["club"].queryset.none()


class ClubMeetingForm(forms.ModelForm):

    # We specify the SplitDateTimeField to have better functionality across browsers.
    # For some reason specifying the widget in the Meta class does not work as expected.
    date = forms.SplitDateTimeField(
        initial=timezone.now,
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            date_format="%Y-%m-%d",
            time_attrs={
                "type": "time",
                "step": "60",
            },  # Only accept 1 minute intervals.
            time_format="%H:%M",
        ),
    )

    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        empty_label="Select a location",
        widget=forms.Select(attrs={"class": "form-control", "id": "location-dropdown"}),
    )
    discussed_books = forms.ModelMultipleChoiceField(
        queryset=ReadingListItem.objects.none(),  # Default: Empty queryset
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = ClubMeeting
        fields = ["date", "location", "discussed_books", "notes"]

        widgets = {
            "date": forms.SplitDateTimeWidget(
                date_attrs={"type": "date"},
                date_format="%Y-%m-%d",
                time_attrs={
                    "type": "time",
                    "step": "60",
                },  # Only accept 1 minute intervals.
                time_format="%H:%M",
            ),
            "notes": forms.Textarea(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        club = kwargs.pop("club", None)
        super().__init__(*args, **kwargs)

        if club:
            # Dynamically getting the locations associated with the club.

            self.fields["location"].queryset = Location.objects.filter(
                id__in=ClubLocation.objects.filter(club=club).values_list(
                    "location", flat=True
                )
            )

            self.fields["discussed_books"].queryset = (
                ReadingListItem.objects.filter(reading_list__club=club)
                .order_by("reading_list")
                .order_by("-created_at")
            )
