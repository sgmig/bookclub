from rest_framework import serializers

from accounts.models import CustomUser
from accounts.serializers import CustomUserSerializer

from books.models import Book
from books.serializers import BookSerializer

from locations.serializers import LocationSerializer
from clubs.models import Club, ClubMembership, ClubMeeting, ReadingList, ReadingListItem


class ClubSerializer(serializers.ModelSerializer):
    members = serializers.StringRelatedField(many=True)  # Display members by name

    class Meta:
        model = Club
        fields = ["id", "name", "description", "members"]


# Club Members Serializer
class ClubMemberSerializer(serializers.ModelSerializer):
    joined_at = serializers.DateTimeField(
        source="date_joined", format="%Y-%m-%d"
    )  # Customize the date format

    class Meta:
        model = ClubMembership
        fields = ["id", "club", "user", "is_admin", "is_active", "joined_at"]


# Reading List Serializers
class ReadingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingList
        fields = ["id", "club", "name", "created_by", "created_at"]


class ReadingListItemSerializer(serializers.ModelSerializer):

    book = BookSerializer()
    added_by = CustomUserSerializer()

    class Meta:
        model = ReadingListItem
        fields = ["id", "reading_list", "book", "added_by", "created_at"]


class ReadingListItemCreateSerializer(serializers.ModelSerializer):

    # Specifying the serializers can be redundant, but let's keep it to be explicit.
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    reading_list = serializers.PrimaryKeyRelatedField(
        queryset=ReadingList.objects.all()
    )

    class Meta:
        model = ReadingListItem
        fields = [
            "reading_list",
            "book",
        ]


# Club Meetings Serializer
class ClubMeetingSerializer(serializers.ModelSerializer):

    discussed_books = ReadingListItemSerializer(many=True)
    location = LocationSerializer()

    class Meta:
        model = ClubMeeting
        fields = ["id", "club", "date", "location", "discussed_books", "notes"]
