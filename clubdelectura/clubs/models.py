from django.db import models
from django.db.models import Avg, Count, Q

from django.conf import settings
from django.utils import timezone

from books.models import Book, BookRating
from locations.models import Location

# Create your models here.
# TODO: Add limits to the textfields to prevent user from adding too much text.


# TODO: Decide on_delete behaviour. The club could remain if the creator user is deleted.
# TODO: Make sure the creator is a member
class Club(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="clubs", through="ClubMembership"
    )

    def __str__(self):
        return self.name

    def next_meeting(self):
        """Get the next meeting for the club."""
        return self.meetings.filter(date__gte=timezone.now()).order_by("date").first()

    # TODO: Restrict to books in the club's reading lists or already discussed in meetings?
    def get_rated_books(self):
        """Get books rated by the club members. Annotate with avg and number of ratings."""

        rated_books = Book.objects.filter(ratings__user__in=self.members.all())

        # Annotate with the average rating and the number of ratings.
        # The number of ratings can be used to select books rated by the whole club.
        rated_books = rated_books.annotate(
            avg_rating=Avg(
                "ratings__rating", filter=Q(ratings__user__in=self.members.all())
            ),
            n_ratings=Count(
                "ratings__user", filter=Q(ratings__user__in=self.members.all())
            ),
        )

        return rated_books


# TODO: The admin field does not do much now, but it will be useful in the future. (I hope)
class ClubMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} in {self.club}"


# TODO: Add a last_modified field.
# TODO: Decide behaviour when deleting a user in the cases where the list has or does not have a club.
class ReadingList(models.Model):
    name = models.CharField(max_length=100)
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="reading_lists",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(default=timezone.now)
    books = models.ManyToManyField(Book, through="ReadingListItem")

    def __str__(self):
        return f"Reading list {self.name}"


# TODO: When deleting a user, should the items in the reading list be deleted or should they be kept?
# TODO: What should happen whith the books added by users who are removed from the club?
class ReadingListItem(models.Model):

    reading_list = models.ForeignKey(
        ReadingList, related_name="reading_list_items", on_delete=models.CASCADE
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reading_list", "book"], name="unique_book_in_reading_list"
            )
        ]

    def __str__(self):
        return f"{self.book} in {self.reading_list}"


class ClubLocation(models.Model):
    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="club_locations"
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="club_locations"
    )

    # Avoid duplicate locations for the same club, it does not make sense.
    constraints = [
        models.UniqueConstraint(
            fields=["club", "location"], name="unique_location_for_club"
        )
    ]

    def __str__(self):
        return f"Meeting place {self.location} for club {self.club}"


# TODO: Add field for the books to be discussed in the meeting.
# This structure means that a book can be discussed in multiple meetings.
# Also, a book can only be discussed in a meeting if it is already part of a reading list.
# This makes sense, but I need to make it easy to add a book to a reading list from the meeting form.
class ClubMeeting(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="meetings")
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )
    date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    discussed_books = models.ManyToManyField(ReadingListItem, related_name="meetings")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.club} meeting at {self.location} on {self.date}"
