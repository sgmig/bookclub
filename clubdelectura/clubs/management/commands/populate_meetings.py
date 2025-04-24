import random
from django.core.management.base import BaseCommand
from faker import Faker
from locations.models import Location
from clubs.models import Club, ClubMeeting, ClubLocation, ReadingListItem

# TODO: Split populaiton between the apps

fake = Faker()


# TODO: Adjust date of the meetings to avoid hard coded dates.
class Command(BaseCommand):
    help = "Populate the database with club meetings. Places and reading lists should be created before."

    def handle(self, *args, **kwargs):
        self.create_clublocations()
        self.create_meetings()  # Adjust number as needed

    def create_clublocations(self):
        """Associate some locations to each club."""
        clubs = Club.objects.all()
        locations = list(Location.objects.all())  # Using a list to randomly sample.

        self.stdout.write("Creating club locations...")
        for club in clubs:
            # Get a random location for the club
            selected_locations = random.sample(locations, random.randint(3, 6))

            # Create a ClubLocation instance

            club_locations = [
                ClubLocation(club=club, location=location)
                for location in selected_locations
            ]
            # Use bulk_create for efficiency
            ClubLocation.objects.bulk_create(club_locations)

        self.stdout.write(self.style.SUCCESS(f"✅ Done!"))

    def create_meetings(self):
        self.stdout.write("Creating meetings...")
        clubs = Club.objects.all()

        for club in clubs:

            min_meetings = 2
            max_meetings = 10

            # Get all locations for the club
            club_locations = [cl.location for cl in club.club_locations.all()]

            meeting_count = random.choice(range(min_meetings, max_meetings))

            reading_list_books = ReadingListItem.objects.filter(reading_list__club=club)

            for i in range(meeting_count):

                # create the meeting
                meeting = ClubMeeting.objects.create(
                    club=club,
                    location=random.choice(club_locations),
                    date=fake.date_time_between(start_date="-6M", end_date="+6M"),
                )

                if reading_list_books:
                    for j in range(random.randint(1, 3)):
                        meeting.discussed_books.add(random.choice(reading_list_books))

                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Added {j+1} books to the meeting.")
                    )

        self.stdout.write(self.style.SUCCESS(f"✅ Created meetings."))
