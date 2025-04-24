import random
from django.core.management.base import BaseCommand
from faker import Faker
from clubs.models import ClubMeeting, ClubLocation


from django.db import IntegrityError

# TODO: Split populaiton between the apps

fake = Faker()


class Command(BaseCommand):
    help = "Associate meeting places with clubs. In this case meetings have been previously created."

    def handle(self, *args, **kwargs):
        self.associate_meeting_places()  # Adjust number as needed

    def associate_meeting_places(self):
        all_meetings = ClubMeeting.objects.all()

        for meeting in all_meetings:
            try:
                ClubLocation.objects.create(
                    club=meeting.club, location=meeting.location
                )
            except IntegrityError as e:
                print(e)
                pass
