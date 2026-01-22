from django.urls import path, include
from locations.views import (
    LocationsViewSet,
)

from rest_framework.routers import DefaultRouter

app_name = "locations"

router = DefaultRouter()

router.register("location", LocationsViewSet, basename="api-location")


urlpatterns = [
    path("api/", include(router.urls)),
]
