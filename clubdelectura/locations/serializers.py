from rest_framework import serializers

from accounts.serializers import CustomUserSerializer
from clubs.models import Club
from locations.models import Location


class LocationSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "address",
            "description",
            "access_details",
            "is_private",
            "created_by",
        ]


class LocationCreateSerializer(serializers.ModelSerializer):
    """Serializer for Location model used in Creation.

    `club` is write-only: if provided, the created location is also linked
    to that club via ClubLocation (see LocationsViewSet.perform_create).
    """

    club = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(), required=False, write_only=True
    )

    class Meta:
        model = Location
        fields = [
            "name",
            "description",
            "address",
            "access_details",
            "is_private",
            "club",
        ]
