# DRF
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

# Create your views here.

from locations.models import Location
from locations.serializers import LocationSerializer, LocationCreateSerializer


@extend_schema(tags=["Locations"])
class LocationsViewSet(ModelViewSet):
    queryset = Location.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return LocationCreateSerializer
        return LocationSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
