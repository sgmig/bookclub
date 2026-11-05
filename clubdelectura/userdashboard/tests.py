from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from books.models import Book, BookRating
from clubs.models import Club, ClubLocation, ClubMembership, ClubMeeting, ReadingList
from locations.models import Location


def make_user(email):
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


class UserDashboardViewTests(TestCase):
    def setUp(self):
        self.user = make_user("dashboard@example.com")
        self.other_user = make_user("other@example.com")

    def test_requires_login(self):
        response = self.client.get(reverse("user_dashboard:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_context_only_includes_current_users_data(self):
        club = Club.objects.create(name="My Club", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=club)

        my_list = ReadingList.objects.create(name="Mine", created_by=self.user)
        ReadingList.objects.create(name="Not Mine", created_by=self.other_user)

        book = Book.objects.create(title="Dune", year=1965)
        my_rating = BookRating.objects.create(book=book, user=self.user, rating=8)
        BookRating.objects.create(book=book, user=self.other_user, rating=3)

        self.client.force_login(self.user)
        response = self.client.get(reverse("user_dashboard:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["clubs"]), [club])
        self.assertEqual(list(response.context["reading_lists"]), [my_list])
        self.assertEqual(list(response.context["book_ratings"]), [my_rating])

    def test_reading_lists_excludes_club_reading_lists(self):
        club = Club.objects.create(name="My Club", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=club)
        personal_list = ReadingList.objects.create(name="Mine", created_by=self.user)
        ReadingList.objects.create(name="Club list", club=club, created_by=self.user)

        self.client.force_login(self.user)
        response = self.client.get(reverse("user_dashboard:dashboard"))

        self.assertEqual(list(response.context["reading_lists"]), [personal_list])

    def test_locations_include_created_and_club_locations(self):
        club = Club.objects.create(name="My Club", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=club)

        my_location = Location.objects.create(name="My Place", created_by=self.user)
        club_location = Location.objects.create(name="Club Venue")
        ClubLocation.objects.create(club=club, location=club_location)
        unrelated_location = Location.objects.create(name="Unrelated")

        self.client.force_login(self.user)
        response = self.client.get(reverse("user_dashboard:dashboard"))

        locations = set(response.context["locations"])
        self.assertEqual(locations, {my_location, club_location})
        self.assertNotIn(unrelated_location, locations)


class UserDashboardClubPreviewViewTests(TestCase):
    def setUp(self):
        self.club, self.member, self.owner = make_club_with_member()
        self.outsider = make_user("outsider@example.com")
        self.url = reverse("user_dashboard:club-preview", kwargs={"pk": self.club.pk})

    def test_member_can_view_preview(self):
        self.client.force_login(self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_non_member_forbidden(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_shows_only_upcoming_meeting(self):
        location = Location.objects.create(name="Library")
        past = ClubMeeting.objects.create(
            club=self.club, location=location, date=timezone.now() - timedelta(days=5)
        )
        upcoming = ClubMeeting.objects.create(
            club=self.club, location=location, date=timezone.now() + timedelta(days=5)
        )

        self.client.force_login(self.member)
        response = self.client.get(self.url)

        self.assertContains(response, upcoming.location.name)
        # The past meeting's own notes/date aren't asserted directly since
        # the panel only ever renders club.next_meeting - there's nothing
        # in the response that would reference `past` at all.
        self.assertEqual(response.context["club"].next_meeting(), upcoming)

    def test_no_upcoming_meeting_message(self):
        self.client.force_login(self.member)

        response = self.client.get(self.url)

        self.assertContains(response, "No upcoming meetings")


class UserDashboardRatingPreviewViewTests(TestCase):
    def setUp(self):
        self.user = make_user("dashboard@example.com")
        self.other_user = make_user("other@example.com")
        self.book = Book.objects.create(title="Dune", year=1965)
        self.rating = BookRating.objects.create(
            book=self.book, user=self.user, rating=8, comment="Great read"
        )
        self.url = reverse(
            "user_dashboard:rating-preview", kwargs={"pk": self.rating.pk}
        )

    def test_owner_can_view_own_rating_preview(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dune")
        self.assertContains(response, "Great read")

    def test_non_owner_cannot_view_someone_elses_rating_preview(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class UserClubListViewTests(TestCase):
    def setUp(self):
        self.user = make_user("dashboard@example.com")

    def test_requires_login(self):
        response = self.client.get(reverse("user_dashboard:user_clubs"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_only_lists_clubs_the_user_belongs_to(self):
        my_club = Club.objects.create(name="My Club", created_by=self.user)
        ClubMembership.objects.create(user=self.user, club=my_club)
        Club.objects.create(name="Someone Else's Club", created_by=self.user)

        self.client.force_login(self.user)
        response = self.client.get(reverse("user_dashboard:user_clubs"))

        self.assertEqual(list(response.context["object_list"]), [my_club])
