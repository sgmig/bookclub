"""
URL configuration for clubdelectura project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from clubs.views import (
    ClubListView,
    ClubDetailView,
    ClubCreateView,
    ClubUpdateView,
    ClubDeleteView,
    ClubBookRatingListView,
    ReadingListDetailView,
    ReadingListPartialDetailView,
    ReadingListCreateView,
    ReadingListUpdateView,
    ReadingListDeleteView,
    ReadingListItemRowView,
    ReadingListItemAddBookView,
    ReadingListItemAutoCompleteView,
    ClubMeetingCreateView,
    ClubMeetingDetailView,
    ClubMeetingUpdateView,
    ClubMeetingDeleteView,
    ClubMeetingPartialDetailView,
    ReadingListItemViewSet,
    ClubMeetingViewSet,
)

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


app_name = "clubs"

router = DefaultRouter()

router.register(
    "reading-list-item", ReadingListItemViewSet, basename="api-reading-list-item"
)
router.register("club-meeting", ClubMeetingViewSet, basename="api-club-meeting")

urlpatterns = [
    path("", ClubListView.as_view(), name="club-list"),
    path("<int:pk>/", ClubDetailView.as_view(), name="club-detail"),
    path("create/", ClubCreateView.as_view(), name="club-create"),
    path("<int:pk>/update/", ClubUpdateView.as_view(), name="club-update"),
    path("<int:pk>/delete/", ClubDeleteView.as_view(), name="club-delete"),
    path(
        "<int:club_id>/book-rating/<int:book_id>/",
        ClubBookRatingListView.as_view(),
        name="club-book-rating",
    ),
    path(
        "reading-list/<int:pk>/",
        ReadingListDetailView.as_view(),
        name="reading-list-detail",
    ),
    path(
        "reading-list/partial/<int:pk>/",
        ReadingListPartialDetailView.as_view(),
        name="reading-list-detail-panel",
    ),
    path(
        "reading-list/create/",
        ReadingListCreateView.as_view(),
        name="reading-list-create",
    ),
    path(
        "reading-list/<int:pk>/update/",
        ReadingListUpdateView.as_view(),
        name="reading-list-update",
    ),
    path(
        "reading-list/<int:pk>/delete/",
        ReadingListDeleteView.as_view(),
        name="reading-list-delete",
    ),
    path(
        "reading-list-item/<int:pk>/row/",
        ReadingListItemRowView.as_view(),
        name="reading-list-item-row",
    ),
    path(
        "reading-list-item/search-book/",
        ReadingListItemAddBookView.as_view(),
        name="reading-list-item-search-book",
    ),
    path(
        "<int:club_id>/reading-list-item/autocomplete/",
        ReadingListItemAutoCompleteView.as_view(),
        name="reading-list-item-autocomplete",
    ),
    path(
        "<int:club_id>/club-meeting/create/",
        ClubMeetingCreateView.as_view(),
        name="club-meeting-create",
    ),
    path(
        "club-meeting/<int:pk>/",
        ClubMeetingDetailView.as_view(),
        name="club-meeting-detail",
    ),
    path(
        "club-meeting/<int:pk>/update/",
        ClubMeetingUpdateView.as_view(),
        name="club-meeting-update",
    ),
    path(
        "club-meeting/<int:pk>/delete/",
        ClubMeetingDeleteView.as_view(),
        name="club-meeting-delete",
    ),
    path(
        "club-meeting/partial/<int:pk>/",
        ClubMeetingPartialDetailView.as_view(),
        name="club-meeting-detail-panel",
    ),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="clubs:schema"),
        name="swagger-ui",
    ),
]
