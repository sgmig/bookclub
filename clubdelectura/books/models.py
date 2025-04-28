from django.db import models
from django.db.models.functions import Lower
from django.db.models import Count

from django.conf import settings

from django.utils import timezone

from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.


# TODO: Add Author country of origin, maybe birthdate.
# Using only name because the Google Books API returns it like that.
class Author(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name

    # Ading indices for case insensitive search.
    # Will be useful for autocomplete and search.
    class Meta:
        indexes = [
            models.Index(fields=["name"]),  # regular index
            models.Index(
                Lower("name"),  # case-insensitive index
                name="author_name_lower_idx",
                fields=[],
            ),
        ]

    @classmethod
    def get_or_create_authors_from_names(cls, authors_names):

        # Collecting or creating Authors from the provided names list.
        # The names are expected to be a list of strings.
        authors = []
        for name in authors_names:
            if name.strip():
                formatted_name = name.strip().title()
                author, _ = Author.objects.get_or_create(name=formatted_name)
                authors.append(author)

        return authors


# TODO: Add collection? Add subtitle? Maybe use as an abstract model and then inherit from it on each published version.
# TODO: Change on_delete beahaviour?.
# TODO: Add a cover image.
# TODO: Add slugfield ?
# TODO: Force title format


class Book(models.Model):
    title = models.CharField(max_length=256)
    authors = models.ManyToManyField(Author, related_name="books")
    year = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.title

    def list_authors(self):
        return ", ".join([author.name for author in self.authors.all()])

    @classmethod
    def filter_by_authors_and_title(cls, title, authors):
        # Shortcut to filter by title (case insensitive) and exact group of authors.
        # It is needed because filtering on ManyToMany fields is not straightforward.
        # TODO: Check if having the same number of authors but including only one of the given ones gives a false positive.
        # Title is a string.
        # Authors is a list of Author objects.

        existing_books = (
            Book.objects.filter(title__iexact=title)
            .filter(authors__in=authors)
            .distinct()
            .annotate(num_authors=Count("authors"))
            .filter(num_authors=len(authors))
        )

        return existing_books


# TODO: They rating could have a modified_at field.
class BookRating(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings"
    )
    rating = models.FloatField(
        default=0.0,
        help_text="Rating between 0 and 10",
        validators=[
            MinValueValidator(0.0),  # Minimum rating of 1
            MaxValueValidator(10.0),  # Maximum rating of 10
        ],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"], name="unique_user_book_rating"
            )
        ]

    def __str__(self):
        return f"{self.book.title} - {self.rating} - {self.user}"
