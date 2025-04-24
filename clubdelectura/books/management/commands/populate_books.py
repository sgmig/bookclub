import random
from django.core.management.base import BaseCommand
from faker import Faker

from books.models import Book, Author

# TODO: Split populaiton between the apps

fake = Faker()


class Command(BaseCommand):
    """Populate the database with fake books and authors."""

    def handle(self, *args, **kwargs):
        n_books = 100  # Adjust number as needed
        n_authors = 30  # Adjust number as needed
        self.create_authors(n_authors)
        self.create_books(n_books)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Database populated with {n_books} books and {n_authors} authors."
            )
        )

    def create_authors(self, count):
        """Create fake authors."""
        self.stdout.write("Creating authors...")
        for _ in range(count):
            Author.objects.create(name=fake.name())
        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} authors."))

    def create_books(self, count):
        """Create fake books. Authors need to be created first."""

        self.stdout.write("Creating books...")
        authors = list(Author.objects.all())

        for _ in range(count):
            book = Book.objects.create(
                title=" ".join(fake.words(random.randint(1, 5), unique=True)).title(),
                year=random.randint(1900, 2025),
            )
            # Assign random authors to the book
            # Each book can have between 1 and 3 authors.
            book.authors.set(random.sample(authors, random.randint(1, 3)))

        self.stdout.write(self.style.SUCCESS(f"✅ Created {count} books."))
