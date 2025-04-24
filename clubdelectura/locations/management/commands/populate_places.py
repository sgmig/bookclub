import random
from django.core.management.base import BaseCommand
from faker import Faker
from locations.models import Location

# TODO: Split populaiton between the apps

fake = Faker()


class Command(BaseCommand):
    help = "Populate the database with fake places"

    def handle(self, *args, **kwargs):
        self.create_locations(20)  # Adjust number as needed

    def create_locations(self, count):
        self.stdout.write("Creating places...")
        location_type = [
            "Restaurant",
            "Cafe",
            "Coworking",
            "House",
            "Appartment",
            "Place",
            "Bar",
        ]
        for _ in range(count):
            Location.objects.create(
                name=fake.first_name() + "'s " + random.choice(location_type),
                address=fake.address(),
            )
        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} locations."))
