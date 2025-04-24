import random
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth import get_user_model
from books.models import Book, BookRating
from clubs.models import Club, ClubMembership

# TODO: Split populaiton between the apps

fake = Faker()
User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with fake users, clubs, and ratings"

    def handle(self, *args, **kwargs):
        self.create_clubs(10)  # Adjust number as needed
        self.assign_users_to_clubs()
        self.create_ratings(100)  # Adjust number as needed

    def create_users(self, count):
        self.stdout.write("Creating users...")
        for _ in range(count):
            User.objects.create_user(
                email=fake.email(),
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )
        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} users."))

    def create_clubs(self, count):
        self.stdout.write("Creating clubs...")

        club_creators = list(User.objects.all())

        for _ in range(count):
            # making sure the club has a creator, and the creator is a member.
            creator = random.choice(club_creators)

            club = Club.objects.create(
                name=fake.company(), description=fake.text(), created_by=creator
            )
            ClubMembership.objects.get_or_create(user=creator, club=club)

        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} clubs."))

    def assign_users_to_clubs(self):
        self.stdout.write("Assigning users to clubs...")
        users = list(User.objects.all())
        clubs = list(Club.objects.all())

        for user in users:
            club = random.choice(clubs)  # Each user joins a random club
            ClubMembership.objects.get_or_create(user=user, club=club)

        self.stdout.write(self.style.SUCCESS(f"✅ Assigned users to clubs."))

    def create_ratings(self, count):
        self.stdout.write("Creating book ratings...")
        users = list(User.objects.all())
        books = list(Book.objects.all())

        for _ in range(count):
            user = random.choice(users)
            book = random.choice(books)
            rating_value = round(random.uniform(1, 10), 1)  # Rating between 1 and 10

            # Ensure the user rates a book only once
            BookRating.objects.update_or_create(
                user=user, book=book, defaults={"rating": rating_value}
            )

        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} ratings."))
