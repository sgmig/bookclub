import random
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth import get_user_model
from books.models import Book, BookRating

# TODO: Split populaiton between the apps

fake = Faker()
User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with fake book ratings. Books and users should be created first."

    def handle(self, *args, **kwargs):
        self.create_ratings(100)  # Adjust number as needed

    def create_ratings(self, count):
        self.stdout.write("Creating book ratings...")
        users = list(User.objects.all())
        books = list(Book.objects.all())

        for _ in range(count):
            user = random.choice(users)
            book = random.choice(books)
            rating_value = round(random.uniform(1, 10), 1)  # Rating between 1 and 10

            # Ensure the user rates a book only once

            update_values = {
                "rating": rating_value,
                "comment": fake.paragraph(nb_sentences=7, variable_nb_sentences=True),
            }

            BookRating.objects.update_or_create(
                user=user, book=book, defaults=update_values
            )

        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} ratings."))
