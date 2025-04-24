import random
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth import get_user_model
from books.models import Book
from clubs.models import Club, ReadingList, ReadingListItem


fake = Faker()
User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with fake users, clubs, and ratings"

    def handle(self, *args, **kwargs):
        self.create_users_readinglists(50)  # Adjust number as needed
        self.create_clubs_readinglists(20)  # Adjust number as needed
        self.add_books_to_readinglists()

    def create_users_readinglists(self, count):
        self.stdout.write("Creating users reading lists...")

        list_owners = list(User.objects.all())
        for _ in range(count):
            owner = random.choice(list_owners)
            ReadingList.objects.create(
                name=" ".join(fake.words(nb=3)).capitalize(), created_by=owner
            )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Created {count} user-owned reading lists.")
        )

    def create_clubs_readinglists(self, count):
        self.stdout.write("Creating users reading lists...")

        clubs = Club.objects.all()
        for _ in range(count):
            club = random.choice(clubs)
            owner = club.created_by

            ReadingList.objects.create(
                name=" ".join(fake.words(nb=3)).capitalize(),
                club=club,
                created_by=owner,
            )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Created {count} club-owned reading lists.")
        )

    def add_books_to_readinglists(self, min_books=1, max_books=10):

        all_lists = ReadingList.objects.all()
        all_books = list(Book.objects.all())

        for reading_list in all_lists:

            # select a random number of books
            n_books = random.choice(range(min_books, max_books))

            books_to_add = random.sample(all_books, n_books)

            club = reading_list.club

            if club:
                for book in books_to_add:
                    ReadingListItem.objects.create(
                        reading_list=reading_list,
                        book=book,
                        added_by=random.choice(club.members.all()),
                    )
            else:
                for book in books_to_add:
                    ReadingListItem.objects.create(
                        reading_list=reading_list,
                        book=book,
                        added_by=reading_list.created_by,
                    )
