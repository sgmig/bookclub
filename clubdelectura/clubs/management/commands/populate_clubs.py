import random
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth import get_user_model
from clubs.models import Club, ClubMembership

# TODO: Split populaiton between the apps

fake = Faker()
User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with fake users, clubs, and ratings"

    def handle(self, *args, **kwargs):
        self.create_clubs(10)  # Adjust number as needed
        self.assign_users_to_clubs()

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
