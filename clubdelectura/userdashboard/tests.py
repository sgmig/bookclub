from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from books.models import Book, BookRating
from clubs.models import Club, ClubMembership, ReadingList


def make_user(email):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="First", last_name="Last"
    )


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
