from rest_framework import serializers

from accounts.models import CustomUser
from accounts.serializers import CustomUserSerializer

from books.models import Book
from books.serializers import BookSerializer

from locations.models import Location
from locations.serializers import LocationSerializer
from clubs.models import (
    Club,
    ClubLocation,
    ClubMembership,
    ClubMeeting,
    ReadingList,
    ReadingListItem,
)


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


# Club Location Serializers
class ClubLocationSerializer(serializers.ModelSerializer):
    """Read/detail serializer - also the fallback for update/partial_update.

    location is read_only here: nested serializers aren't writable without
    a custom update(), and there's no UI or need to change which Location a
    ClubLocation points to after creation (only .club/.location themselves
    get edited by deleting and recreating the link, which this branch
    doesn't build UI for either - see docs/LOCATIONS_DESIGN.md non-goals).
    Without this, a PATCH/PUT including `location` would hit the same
    "doesn't support writable nested fields" crash as ClubMeetingSerializer.
    """

    location = LocationSerializer(read_only=True)

    class Meta:
        model = ClubLocation
        fields = ["id", "club", "location"]


class ClubLocationCreateSerializer(serializers.ModelSerializer):

    # Both reference existing objects - creating the Location itself is a
    # separate call to the locations app's own API. This endpoint only
    # creates the link between an existing Location and an existing Club.
    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())

    class Meta:
        model = ClubLocation
        fields = ["club", "location"]


# Club Meetings Serializer
class ClubMeetingSerializer(serializers.ModelSerializer):
    """Read/detail serializer - not used for create/update (see
    ClubMeetingCreateSerializer below). location and discussed_books are
    read_only: nested serializers aren't writable without a custom
    create()/update(), which is exactly what previously made every
    create/update against this endpoint crash with "doesn't support
    writable nested fields".
    """

    discussed_books = ReadingListItemSerializer(many=True, read_only=True)
    location = LocationSerializer(read_only=True)

    class Meta:
        model = ClubMeeting
        fields = ["id", "club", "date", "location", "discussed_books", "notes"]


class ClubMeetingCreateSerializer(serializers.ModelSerializer):
    """Serializer for ClubMeeting used for create/update.

    All relations are PrimaryKeyRelatedFields referencing existing objects,
    mirroring ReadingListItemCreateSerializer/ClubLocationCreateSerializer -
    creating a new Location or ReadingListItem is a separate call to their
    own APIs.
    """

    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all())
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, allow_null=True
    )
    discussed_books = serializers.PrimaryKeyRelatedField(
        queryset=ReadingListItem.objects.all(), many=True, required=False
    )

    class Meta:
        model = ClubMeeting
        fields = ["club", "date", "location", "discussed_books", "notes"]
