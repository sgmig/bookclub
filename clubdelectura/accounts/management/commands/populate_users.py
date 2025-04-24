import random
from django.core.management.base import BaseCommand
from faker import Faker

from accounts.models import CustomUser


# Create users using the CustomUser model

fake = Faker()


class Command(BaseCommand):
    help = "Populate the database with fake users"

    def handle(self, *args, **kwargs):
        self.create_users(50)

    def create_users(self, count):
        self.stdout.write("Creating users...")
        for _ in range(count):
            CustomUser.objects.create_user(
                email=fake.email(),
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )
        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} users."))
