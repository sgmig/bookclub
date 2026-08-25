from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from clubs.models import Club, ClubLocation, ClubMembership
from locations.forms import LocationForm
from locations.models import Location


def make_user(email="reader@example.com"):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="First", last_name="Last"
    )


def make_club_with_member(
    name="Book Lovers", email="member@example.com", owner_email="owner@example.com"
):
    owner = make_user(owner_email)
    club = Club.objects.create(name=name, created_by=owner)
    member = make_user(email)
    ClubMembership.objects.create(user=member, club=club)
    ClubMembership.objects.create(user=owner, club=club)
    return club, member, owner


class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        location = Location.objects.create(name="Central Library", address="Main St")
        self.assertEqual(str(location), "Central Library")


class RedactForDepartedMemberTests(TestCase):
    # Tests Location.redact_for_departed_member() directly. The signal that
    # calls it on membership removal/deactivation lives in clubs/signals.py
    # and is tested in clubs.tests.MembershipRedactionSignalTests.
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()

    def test_redacts_private_location_details_keeping_name(self):
        location = Location.objects.create(
            name="Jane's Place",
            address="123 Main St",
            access_details="Buzzer 4",
            description="Cozy apartment",
            created_by=self.member,
            is_private=True,
        )
        ClubLocation.objects.create(club=self.club, location=location)

        Location.redact_for_departed_member(self.member, self.club)

        location.refresh_from_db()
        self.assertEqual(location.name, "Jane's Place")
        self.assertEqual(location.address, "")
        self.assertEqual(location.access_details, "")
        self.assertEqual(location.description, "")

    def test_does_not_redact_public_locations(self):
        location = Location.objects.create(
            name="Public Library",
            address="1 Book Rd",
            created_by=self.member,
            is_private=False,
        )
        ClubLocation.objects.create(club=self.club, location=location)

        Location.redact_for_departed_member(self.member, self.club)

        location.refresh_from_db()
        self.assertEqual(location.address, "1 Book Rd")

    def test_does_not_redact_another_users_location(self):
        location = Location.objects.create(
            name="Owner's Place",
            address="2 Owner Rd",
            created_by=self.owner,
            is_private=True,
        )
        ClubLocation.objects.create(club=self.club, location=location)

        Location.redact_for_departed_member(self.member, self.club)

        location.refresh_from_db()
        self.assertEqual(location.address, "2 Owner Rd")

    def test_does_not_redact_location_tied_to_a_different_club(self):
        other_club = Club.objects.create(name="Other Club", created_by=self.owner)
        location = Location.objects.create(
            name="Jane's Other Place",
            address="3 Elsewhere Rd",
            created_by=self.member,
            is_private=True,
        )
        ClubLocation.objects.create(club=other_club, location=location)

        Location.redact_for_departed_member(self.member, self.club)

        location.refresh_from_db()
        self.assertEqual(location.address, "3 Elsewhere Rd")


class LocationFormTests(TestCase):
    def test_is_private_is_not_required(self):
        # Regression test: Location.is_private previously had no blank=True,
        # so the auto-generated form field defaulted to required=True -
        # meaning a user could never actually uncheck it (mark a location
        # public) without a validation error.
        form = LocationForm(
            data={"name": "Public Cafe", "address": "1 Coffee Rd"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["is_private"])

    def test_valid_with_is_private_checked(self):
        form = LocationForm(
            data={"name": "Jane's Place", "address": "1 Home Rd", "is_private": "on"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["is_private"])


class LocationsAPITests(TestCase):
    # Deliberately club-agnostic: LocationsViewSet only knows about the
    # Location resource itself. Attaching a location to a club is a
    # separate call to clubs:api-club-location-list - see
    # clubs.tests.ClubLocationAPITests.
    def setUp(self):
        self.user = make_user()
        self.list_url = reverse("locations:api-location-list")

    def test_list_requires_authentication(self):
        response = self.client.get(self.list_url)
        # DRF falls back to 403 (not 401) here because SessionAuthentication
        # is checked before BasicAuthentication and doesn't set a
        # WWW-Authenticate challenge header.
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_list_locations(self):
        Location.objects.create(name="Central Library")
        self.client.force_login(self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_authenticated_user_can_create_location(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.list_url, {"name": "New Cafe", "address": "1 Coffee Rd"}
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Location.objects.filter(name="New Cafe").exists())

    def test_create_sets_created_by_and_never_links_a_club(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.list_url, {"name": "Personal Spot", "address": "9 Solo Rd"}
        )

        self.assertEqual(response.status_code, 201)
        location = Location.objects.get(name="Personal Spot")
        self.assertEqual(location.created_by, self.user)
        self.assertFalse(ClubLocation.objects.filter(location=location).exists())
