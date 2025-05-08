# Generic django
from django.shortcuts import render, get_object_or_404

from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden

# DRF
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, ListCreateAPIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter

# Own imports
from clubs.serializers import (
    ClubSerializer,
    ReadingListItemSerializer,
    ReadingListItemCreateSerializer,
    ClubMeetingSerializer,
)

from clubs.models import Club, ClubMeeting, ReadingList, ReadingListItem

from clubs.forms import ClubForm, ClubMeetingForm, ReadingListForm

from books.models import Book, BookRating
from books.forms import GoogleBooksSearchForm
from books.integrations.google_books import GoogleBooksAPI

# Create your views here.


class IndexView(TemplateView):
    template_name = "clubs/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["my_content"] = "BASIC CONTENT"

        return context


# Club views
class ClubListView(ListView):
    model = Club


class ClubDetailView(DetailView):
    model = Club
    template_name = "clubs/club_detail.html"

    def get_context_data(self, **kwargs):
        """Passing context explicitly for clarity."""
        context = super().get_context_data(**kwargs)
        context["members"] = self.object.members.all()  # Get all club members
        context["reading_lists"] = (
            self.object.reading_lists.all()
        )  # Club’s reading lists
        context["meetings"] = self.object.meetings.order_by("-date")  # Club meetings
        context["next_meeting"] = self.object.next_meeting()  # Next meeting
        context["rated_books"] = self.object.get_rated_books().order_by(
            "-n_ratings"
        )  # Rated books
        return context


class ClubCreateView(CreateView):
    model = Club
    form_class = ClubForm
    success_url = reverse_lazy("club_list")


class ClubUpdateView(UpdateView):
    model = Club
    form_class = ClubForm
    success_url = reverse_lazy("club_list")


class ClubDeleteView(DeleteView):
    model = Club
    success_url = reverse_lazy("club_list")


# ReadingList Views


class ReadingListDetailView(LoginRequiredMixin, DetailView):
    model = ReadingList
    template_name = "clubs/reading_list_detail.html"
    context_object_name = "reading_list"


# TODO: See who can edit lists
class ReadingListPartialDetailView(LoginRequiredMixin, DetailView):
    model = ReadingList
    template_name = "clubs/partials/reading_list_detail_panel.html"
    context_object_name = "reading_list"

    def dispatch(self, request, *args, **kwargs):
        reading_list = self.get_object()

        # If there is a club, we check if the user is a member. If there is no club, we check if the user is the creator.
        if reading_list.club:
            if (
                request.user not in reading_list.club.members.all()
            ):  # Check the user is clubmember
                return HttpResponseForbidden(
                    "You are not allowed to view this reading list."
                )
        elif reading_list.created_by != request.user:
            return HttpResponseForbidden(
                "You are not allowed to view this reading list."
            )

        return super().dispatch(request, *args, **kwargs)


class ReadingListCreateView(CreateView):
    model = ReadingList
    form_class = ReadingListForm
    template_name = "clubs/reading_list_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.club = None
        club_id = self.request.GET.get("club_id")
        if club_id:
            self.club = get_object_or_404(Club, id=club_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["club"] = self.club
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "clubs:reading-list-detail", kwargs={"pk": self.object.id}
        )  # Redirect to details page


class ReadingListUpdateView(UpdateView):
    model = ReadingList
    form_class = ReadingListForm
    template_name = "clubs/reading_list_form.html"
    context_object_name = "reading_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["club"] = self.object.club  # Get the club from the reading list instance
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            "clubs:reading-list-detail", kwargs={"pk": self.object.id}
        )  # Redirect to details page


class ReadingListDeleteView(DeleteView):
    model = ReadingList
    template_name = "clubs/reading_list_delete_confirmation.html"
    context_object_name = "reading_list"

    def get_success_url(self):
        # Concatenate the URL with the hash to redirect to the meetings tab.
        return (
            reverse_lazy("clubs:club-detail", kwargs={"pk": self.object.club.id})
            + "#reading-lists"
        )


# ReadingListItem views. I'll use the API for most things, but for searching and adding books
# we need to render a form.
class ReadingListItemAddBookView(LoginRequiredMixin, FormView):
    form_class = GoogleBooksSearchForm
    template_name = "clubs/partials/add_reading_list_item_modal.html"

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.

        books_api = GoogleBooksAPI()
        # pass the form data to the search volumes method
        response = books_api.search_volumes(**form.cleaned_data)
        print("Google Books API response:", response)
        if response:
            results = response.json().get("items", [])

        print(f"Found {len(results)} results")

        return render(
            self.request,
            "clubs/partials/add_reading_list_item_modal.html",
            {"form": form, "results": results},
        )


class ReadingListItemRowView(LoginRequiredMixin, DetailView):
    model = ReadingListItem
    template_name = "clubs/partials/reading_list_item_row.html"
    context_object_name = "reading_list_item"

    def dispatch(self, request, *args, **kwargs):
        reading_list_item = self.get_object()
        # If there is a club, we check if the user is a member.
        # If there is no club, we check if the user is the creator.
        if reading_list_item.reading_list.club:
            if request.user not in reading_list_item.reading_list.club.members.all():
                # Check the user is clubmember
                return HttpResponseForbidden(
                    "You are not allowed to view this reading list item."
                )
        elif (
            request.user != reading_list_item.created_by
        ):  # Check the user is the creator
            return HttpResponseForbidden(
                "You are not allowed to view this reading list item."
            )

        return super().dispatch(request, *args, **kwargs)


# ClubMeeting views


class ClubMeetingDetailView(LoginRequiredMixin, DetailView):

    model = ClubMeeting
    template_name = "clubs/club_meeting_detail.html"
    context_object_name = "club_meeting"

    def dispatch(self, request, *args, **kwargs):
        club_meeting = self.get_object()
        if (
            request.user not in club_meeting.club.members.all()
        ):  # Check the user is clubmember
            return HttpResponseForbidden("You are not allowed to view this meeting.")
        return super().dispatch(request, *args, **kwargs)


class ClubMeetingPartialDetailView(LoginRequiredMixin, DetailView):
    model = ClubMeeting
    template_name = "clubs/partials/club_meeting_detail_panel.html"
    context_object_name = "club_meeting"

    def dispatch(self, request, *args, **kwargs):
        club_meeting = self.get_object()
        if (
            request.user not in club_meeting.club.members.all()
        ):  # Check the user is clubmember
            return HttpResponseForbidden("You are not allowed to view this meeting.")
        return super().dispatch(request, *args, **kwargs)


class ClubMeetingCreateView(CreateView):
    model = ClubMeeting
    form_class = ClubMeetingForm
    template_name = "clubs/club_meeting_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["club"] = get_object_or_404(Club, id=self.kwargs["club_id"])
        return context

    def get_form_kwargs(self):
        # Get the default kwargs for the form and add the 'club' instance
        kwargs = super().get_form_kwargs()

        kwargs["club"] = get_object_or_404(Club, id=self.kwargs["club_id"])

        return kwargs

    def form_valid(self, form):
        club = get_object_or_404(Club, id=self.kwargs["club_id"])
        form.instance.club = club  # Assign club before saving
        return super().form_valid(form)

    def get_success_url(self):
        return (
            reverse_lazy("clubs:club-detail", kwargs={"pk": self.object.club.id})
            + "#meetings"
        )  # Redirect to club page, on the meetings tab


class ClubMeetingUpdateView(UpdateView):
    model = ClubMeeting
    form_class = ClubMeetingForm
    template_name = "clubs/club_meeting_form.html"
    context_object_name = "club_meeting"

    def get_form_kwargs(self):
        # Get the meeting instance
        meeting = self.get_object()  # Get the object being edited (the meeting)

        # Get the default kwargs for the form and add the 'meeting' instance
        kwargs = super().get_form_kwargs()

        kwargs["club"] = meeting.club

        return kwargs

    def get_success_url(self):
        return reverse_lazy("clubs:club-meeting-detail", kwargs={"pk": self.object.pk})


class ClubMeetingDeleteView(DeleteView):
    model = ClubMeeting
    template_name = "clubs/club_meeting_delete_confirmation.html"
    context_object_name = "club_meeting"

    def get_success_url(self):
        # Concatenate the URL with the hash to redirect to the meetings tab.
        return (
            reverse_lazy("clubs:club-detail", kwargs={"pk": self.object.club.id})
            + "#meetings"
        )


class ClubBookRatingListView(LoginRequiredMixin, ListView):
    model = BookRating
    template_name = "books/partials/book_rating_table.html"
    context_object_name = "book_ratings"

    def get_queryset(self):
        # Get the club from the URL parameters

        club_id = self.kwargs.get("club_id")
        book_id = self.kwargs.get("book_id")

        club = get_object_or_404(Club, id=club_id)
        book = get_object_or_404(Book, id=book_id)

        self.book = book  # Store the book for later use in the context

        # check user is clubmemeber
        if self.request.user not in club.members.all():
            return HttpResponseForbidden(
                "You are not allowed to view these book ratings."
            )

        return BookRating.objects.filter(
            user__in=club.members.all(), book=book
        ).order_by("-rating")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["book"] = self.book  # Add the book to the context
        return context


# API views
@extend_schema(tags=["Reading List Items"])
class ReadingListItemViewSet(ModelViewSet):

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ReadingListItemCreateSerializer
        elif self.action in ["retrieve", "list"]:
            return ReadingListItemSerializer
        return ReadingListItemSerializer

    def get_queryset(self):
        queryset = ReadingListItem.objects.all()
        reading_list_id = self.request.query_params.get("reading_list_id")
        if reading_list_id:
            queryset = queryset.filter(reading_list_id=reading_list_id)
        return queryset

    def perform_create(self, serializer):
        # Save the instance using the CreateSerializer
        serializer.save(added_by=self.request.user)

    @extend_schema(
        request=ReadingListItemCreateSerializer,
        responses={201: ReadingListItemSerializer},
    )
    def create(self, request, *args, **kwargs):
        # Use the CreateSerializer for input validation
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)

        # Re-serialize the created instance using the detail serializer
        detail_serializer = ReadingListItemSerializer(
            create_serializer.instance, context=self.get_serializer_context()
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="reading_list_id",
                description="Filter by reading list ID",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all reading list items, optionally filtered by `reading_list_id`."""
        return super().list(request, *args, **kwargs)


@extend_schema(tags=["Club Meetings"])
class ClubMeetingViewSet(ModelViewSet):
    serializer_class = ClubMeetingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ClubMeeting.objects.all()
        club_id = self.request.query_params.get("club_id")
        if club_id:
            queryset = queryset.filter(club_id=club_id)
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="club_id",
                description="Filter by club ID",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all reading list items, optionally filtered by `club_id`."""
        return super().list(request, *args, **kwargs)
