from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from locations.models import Location


def make_user(email="reader@example.com"):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="First", last_name="Last"
    )


class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        location = Location.objects.create(name="Central Library", address="Main St")
        self.assertEqual(str(location), "Central Library")


class LocationsAPITests(TestCase):
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
