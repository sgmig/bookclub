from django.shortcuts import get_object_or_404

from django.views.generic import FormView

# DRF
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

# Create your views here.

from clubs.mixins import ClubMemberRequiredMixin
from clubs.models import Club, ClubLocation
from locations.forms import LocationForm
from locations.models import Location
from locations.permissions import IsClubMemberForLocationCreate
from locations.serializers import LocationSerializer, LocationCreateSerializer


@extend_schema(tags=["Locations"])
class LocationsViewSet(ModelViewSet):
    queryset = Location.objects.all()
    permission_classes = [IsAuthenticated, IsClubMemberForLocationCreate]

    def get_serializer_class(self):
        if self.action == "create":
            return LocationCreateSerializer
        return LocationSerializer

    def perform_create(self, serializer):
        club = serializer.validated_data.pop("club", None)
        serializer.save(created_by=self.request.user)
        if club:
            ClubLocation.objects.get_or_create(club=club, location=serializer.instance)

    @extend_schema(
        request=LocationCreateSerializer,
        responses={201: LocationSerializer},
    )
    def create(self, request, *args, **kwargs):
        # Use the CreateSerializer for input validation
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)

        # Re-serialize the created instance using the detail serializer
        detail_serializer = LocationSerializer(
            create_serializer.instance, context=self.get_serializer_context()
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class LocationCreateModalView(ClubMemberRequiredMixin, FormView):
    form_class = LocationForm
    template_name = "locations/partials/location_create_modal.html"

    def get_club(self):
        return get_object_or_404(Club, id=self.kwargs["club_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["club"] = self.get_club()
        return context
