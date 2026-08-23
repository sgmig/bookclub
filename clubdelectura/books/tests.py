from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from books.integrations.google_books import parse_year_from_publication_date
from books.models import Author, Book, BookRating


def make_user(email="reader@example.com"):
    return CustomUser.objects.create_user(
        email=email, password="password123", first_name="Book", last_name="Worm"
    )


class AuthorModelTests(TestCase):
    def test_get_or_create_authors_from_names_creates_and_title_cases(self):
        authors = Author.get_or_create_authors_from_names(["  jane austen  ", "mark twain"])

        self.assertEqual([a.name for a in authors], ["Jane Austen", "Mark Twain"])
        self.assertEqual(Author.objects.count(), 2)

    def test_get_or_create_authors_from_names_dedupes_existing(self):
        Author.objects.create(name="Jane Austen")

        authors = Author.get_or_create_authors_from_names(["Jane Austen"])

        self.assertEqual(Author.objects.count(), 1)
        self.assertEqual(authors[0], Author.objects.get(name="Jane Austen"))

    def test_get_or_create_authors_from_names_skips_blank_entries(self):
        authors = Author.get_or_create_authors_from_names(["", "   ", "Toni Morrison"])

        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0].name, "Toni Morrison")


class BookModelTests(TestCase):
    def setUp(self):
        self.austen = Author.objects.create(name="Jane Austen")
        self.twain = Author.objects.create(name="Mark Twain")

    def test_filter_by_authors_and_title_matches_exact_author_set(self):
        book = Book.objects.create(title="Collaboration", year=2000)
        book.authors.set([self.austen, self.twain])

        matches = Book.filter_by_authors_and_title(
            "Collaboration", [self.austen, self.twain]
        )

        self.assertIn(book, matches)

    def test_filter_by_authors_and_title_false_positive_on_partial_author_match(self):
        # Documents a known limitation flagged by the TODO on
        # Book.filter_by_authors_and_title: num_authors is computed from the
        # already-filtered join, not the book's true total author count, so
        # a book with two authors currently matches a lookup for just one of
        # them. Not fixed here (out of scope for this pass) - see
        # docs/JOURNAL.md.
        book = Book.objects.create(title="Collaboration", year=2000)
        book.authors.set([self.austen, self.twain])

        matches = Book.filter_by_authors_and_title("Collaboration", [self.austen])

        self.assertIn(book, matches)

    def test_filter_by_authors_and_title_is_case_insensitive(self):
        book = Book.objects.create(title="Pride and Prejudice", year=1813)
        book.authors.set([self.austen])

        matches = Book.filter_by_authors_and_title(
            "pride and prejudice", [self.austen]
        )

        self.assertIn(book, matches)

    def test_list_authors_joins_names(self):
        book = Book.objects.create(title="Collaboration", year=2000)
        book.authors.set([self.austen, self.twain])

        self.assertEqual(book.list_authors(), "Jane Austen, Mark Twain")


class BookRatingModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = Book.objects.create(title="Moby Dick", year=1851)

    def test_unique_rating_per_user_and_book(self):
        BookRating.objects.create(book=self.book, user=self.user, rating=8)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BookRating.objects.create(book=self.book, user=self.user, rating=5)

    def test_different_users_can_rate_the_same_book(self):
        other_user = make_user(email="other@example.com")
        BookRating.objects.create(book=self.book, user=self.user, rating=8)

        # Should not raise.
        BookRating.objects.create(book=self.book, user=other_user, rating=6)

        self.assertEqual(self.book.ratings.count(), 2)


class ParseYearFromPublicationDateTests(TestCase):
    def test_full_date(self):
        self.assertEqual(parse_year_from_publication_date("2023-10-01"), 2023)

    def test_year_month(self):
        self.assertEqual(parse_year_from_publication_date("2023-10"), 2023)

    def test_year_only(self):
        self.assertEqual(parse_year_from_publication_date("2023"), 2023)

    def test_unrecognized_format_returns_none(self):
        self.assertIsNone(parse_year_from_publication_date(""))


class BookRatingCreateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = Book.objects.create(title="Moby Dick", year=1851)
        self.client.force_login(self.user)

    def test_create_rating(self):
        response = self.client.post(
            reverse("books:book-rating-create") + f"?book_id={self.book.pk}",
            {"book": self.book.pk, "rating": 7, "comment": "Solid."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BookRating.objects.filter(book=self.book, user=self.user).exists()
        )

    def test_visiting_create_with_existing_rating_redirects_to_update(self):
        rating = BookRating.objects.create(book=self.book, user=self.user, rating=9)

        response = self.client.get(
            reverse("books:book-rating-create") + f"?book_id={self.book.pk}"
        )

        self.assertRedirects(
            response,
            reverse("books:book-rating-update", kwargs={"pk": rating.pk}),
        )

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("books:book-rating-create") + f"?book_id={self.book.pk}"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class BookViewSetCreateFromSearchTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("books:api-book-create-from-search")

    def test_creates_new_book_with_authors(self):
        response = self.client.post(
            self.url,
            {
                "title": "the hobbit",
                "authors": "J.R.R. Tolkien",
                "published_date": "1937-09-21",
            },
        )

        self.assertEqual(response.status_code, 201)
        book = Book.objects.get(title="The Hobbit")
        self.assertEqual(book.year, 1937)
        self.assertEqual(list(book.authors.values_list("name", flat=True)), ["J.R.R. Tolkien"])

    def test_returns_existing_book_instead_of_duplicating(self):
        author = Author.objects.create(name="J.R.R. Tolkien")
        existing = Book.objects.create(title="The Hobbit", year=1937)
        existing.authors.set([author])

        response = self.client.post(
            self.url,
            {"title": "the hobbit", "authors": "J.R.R. Tolkien"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], existing.pk)
        self.assertEqual(Book.objects.filter(title="The Hobbit").count(), 1)

    def test_requires_title_and_authors(self):
        response = self.client.post(self.url, {"title": "", "authors": ""})

        self.assertEqual(response.status_code, 400)

    def test_anonymous_request_is_rejected(self):
        self.client.logout()

        response = self.client.post(
            self.url, {"title": "the hobbit", "authors": "J.R.R. Tolkien"}
        )

        # DRF falls back to 403 (not 401) here because SessionAuthentication
        # is checked before BasicAuthentication and doesn't set a
        # WWW-Authenticate challenge header.
        self.assertEqual(response.status_code, 403)


class BookRatingViewSetOwnershipTests(TestCase):
    # Regression coverage: BookRatingViewSet used to only check
    # IsAuthenticated, with no ownership check - any authenticated user
    # could PATCH/PUT/DELETE any other user's rating via the API.
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.other_user = make_user("other@example.com")
        self.book = Book.objects.create(title="Dune", year=1965)
        self.rating = BookRating.objects.create(
            book=self.book, user=self.owner, rating=8
        )
        self.detail_url = reverse(
            "books:api-book-rating-detail", kwargs={"pk": self.rating.pk}
        )

    def test_owner_can_update_own_rating(self):
        self.client.force_login(self.owner)

        response = self.client.patch(
            self.detail_url,
            {"rating": 9},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.rating.refresh_from_db()
        self.assertEqual(self.rating.rating, 9)

    def test_non_owner_cannot_update_rating(self):
        self.client.force_login(self.other_user)

        response = self.client.patch(
            self.detail_url,
            {"rating": 1},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.rating.refresh_from_db()
        self.assertEqual(self.rating.rating, 8)

    def test_non_owner_cannot_delete_rating(self):
        self.client.force_login(self.other_user)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(BookRating.objects.filter(pk=self.rating.pk).exists())

    def test_owner_can_delete_own_rating(self):
        self.client.force_login(self.owner)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(BookRating.objects.filter(pk=self.rating.pk).exists())

    def test_non_owner_can_still_list_and_retrieve(self):
        # Reads stay open - ratings are meant to be visible across users,
        # only mutation is owner-restricted.
        self.client.force_login(self.other_user)

        list_response = self.client.get(reverse("books:api-book-rating-list"))
        detail_response = self.client.get(self.detail_url)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
