import random
from django.core.management.base import BaseCommand
from faker import Faker
from locations.models import Location
from clubs.models import Club, ClubMeeting, ReadingListItem

# TODO: Split populaiton between the apps

fake = Faker()


# TODO: Adjust date of the meetings to avoid hard coded dates.
class Command(BaseCommand):
    help = "Populate the database with fake places"

    def handle(self, *args, **kwargs):
        self.create_meetings()  # Adjust number as needed

    def create_meetings(self):
        self.stdout.write("Creating places...")

        clubs = Club.objects.all()

        all_places = Location.objects.all()
        for club in clubs:

            min_meetings = 2
            max_meetings = 10

            meeting_count = random.choice(range(min_meetings, max_meetings))

            reading_list_books = ReadingListItem.objects.filter(reading_list__club=club)

            for i in range(meeting_count):

                # create the meeting
                meeting = ClubMeeting.objects.create(
                    club=club,
                    location=random.choice(all_places),
                    date=fake.date_between(start_date="-6M", end_date="+6M"),
                )

                if reading_list_books:
                    for j in range(random.randint(1, 3)):
                        meeting.discussed_books.add(random.choice(reading_list_books))

                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Added {j+1} books to the meeting.")
                    )

        self.stdout.write(self.style.SUCCESS(f"✅ Created meetings."))
