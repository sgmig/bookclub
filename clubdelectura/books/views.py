import requests
from datetime import datetime

from django.conf import settings

from django.db.models import Count, Q

from django.contrib.auth import get_user_model

from django import forms

from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.urls import reverse_lazy
from django.views import View
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

# DRF
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


# django autocomplete-light
from dal import autocomplete

from books.models import Book, Author, BookRating
from books.forms import GoogleBooksSearchForm, BookForm, BookRatingForm
from books.serializers import (
    BookSerializer,
    BookRatingSerializer,
    BookRatingCreateSerializer,
)
from books.integrations.google_books import (
    GoogleBooksAPI,
    parse_year_from_publication_date,
)

# Defining the user model. Used in ratings.
User = get_user_model()

# Create your views here.
# TODO: Add authentication everywhere.


# TODO: Turn into class-based view.
# TODO: Add pagination.
# TODO: Handle errors and empty results.
def google_books_search(request):
    results = []
    form = GoogleBooksSearchForm(request.GET or None)

    if form.is_valid():
        books_api = GoogleBooksAPI()
        # pass the form data to the search volumes method
        response = books_api.search_volumes(**form.cleaned_data)
        if response:
            results = response.json().get("items", [])

    return render(
        request,
        "books/google_books_search.html",
        {"form": form, "results": results},
    )


class BookSearchView(LoginRequiredMixin, FormView):
    form_class = GoogleBooksSearchForm
    template_name = "books/google_books_search.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data"] = self.request.GET  # instead of POST
        return kwargs

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        results = []

        print(request.GET)

        if form.is_valid():
            books_api = GoogleBooksAPI()
            response = books_api.search_volumes(**form.cleaned_data)
            if response:
                results = response.json().get("items", [])

        return self.render_to_response(
            self.get_context_data(form=form, results=results)
        )


class BookSearchViewModule(LoginRequiredMixin, FormView):
    form_class = GoogleBooksSearchForm
    template_name = "books/partials/google_books_search_module.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data"] = self.request.GET  # instead of POST
        return kwargs

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        results = []

        print(request.GET)

        if form.is_valid():

            books_api = GoogleBooksAPI()
            response = books_api.search_volumes(**form.cleaned_data)
            if response:
                results = response.json().get("items", [])

        return self.render_to_response(
            self.get_context_data(form=form, results=results)
        )


class BookCreateView(CreateView):
    model = Book
    form_class = BookForm
    template_name = "books/book_form.html"

    def get_success_url(self):
        return reverse_lazy("books:book-detail", kwargs={"pk": self.object.pk})


class BookUpdateView(UpdateView):
    model = Book
    form_class = BookForm
    template_name = "books/book_form.html"


class BookDetailView(DetailView):
    model = Book
    template_name = "books/book_detail.html"
    context_object_name = "book"


# TODO: Check permissions for book ratings.
class BookRatingListView(ListView):
    model = BookRating
    template_name = "books/book_rating_list.html"
    context_object_name = "book_ratings"

    def dispatch(self, request, *args, **kwargs):
        book_id = request.GET.get("book_id")
        user_ids = request.GET.getlist("user_id")

        self.book = get_object_or_404(Book, pk=book_id) if book_id else None

        self.users = get_list_or_404(User, pk__in=user_ids) if user_ids else None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Get the queryset of book ratings.
        # Filter by book and users if provided.
        bookrating_filters = dict()
        if self.book:
            bookrating_filters["book"] = self.book
        if self.users:
            bookrating_filters["user__in"] = self.users

        return (
            BookRating.objects.filter(**bookrating_filters)
            .order_by("book__title")
            .order_by("-rating")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["book"] = self.book
        context["users"] = self.users
        return context


class BookRatingCreateView(LoginRequiredMixin, CreateView):
    model = BookRating
    form_class = BookRatingForm
    template_name = "books/book_rating_form.html"
    context_object_name = "book_rating"

    def dispatch(self, request, *args, **kwargs):
        self.book = None
        book_id = self.request.GET.get("book_id")
        if book_id:
            # Get the book instance
            self.book = get_object_or_404(Book, pk=book_id)

            # Check for existing rating by this user
            existing_rating = BookRating.objects.filter(
                book=self.book, user=self.request.user
            ).first()
            if existing_rating:
                return redirect("books:book-rating-update", pk=existing_rating.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # The book has been set in the dispatch method.
        if self.book:
            # Add the book instance to the form kwargs
            kwargs["book"] = self.book

        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return (
            reverse_lazy("books:book-rating-list") + f"?book_id={self.object.book.pk}"
        )


class BookRatingUpdateView(LoginRequiredMixin, UpdateView):
    model = BookRating
    form_class = BookRatingForm
    template_name = "books/book_rating_form.html"
    context_object_name = "book_rating"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Add the book instance to the form kwargs
        print(f"Book rating update view: {self.object.book}")
        kwargs["book"] = self.object.book  # Get the book from the rating
        return kwargs

    def get_success_url(self):
        return (
            reverse_lazy("books:book-rating-list") + f"?book_id={self.object.book.pk}"
        )


class BookRatingModalView(LoginRequiredMixin, FormView):
    form_class = BookRatingForm
    template_name = "books/partials/book_rating_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.book_rating = None
        self.book = None
        # Check if book_rating_id is provided in the GET parameters
        book_rating_id = self.request.GET.get("book_rating_id")
        if book_rating_id:
            self.book_rating = get_object_or_404(BookRating, id=book_rating_id)
        else:
            book_id = self.request.GET.get("book_id")
            if book_id:
                # Get the book instance
                book = get_object_or_404(Book, pk=book_id)

                # Check for existing rating by this user
                existing_rating = BookRating.objects.filter(
                    book=book, user=self.request.user
                ).first()
                if existing_rating:
                    self.book_rating = existing_rating
                else:
                    # Prefill the form with the book instance
                    self.book = book

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Add the book instance to the form kwargs
        if self.book_rating:
            kwargs["instance"] = self.book_rating
            kwargs["book"] = self.book_rating.book  # Get the book from the rating
            print(f"Book rating update view: {self.book_rating.book}")
        elif self.book:
            kwargs["book"] = self.book
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["book_rating"] = self.book_rating  # Add the book_rating to the context
        return context


class BookRatingDeleteView(LoginRequiredMixin, DeleteView):
    model = BookRating
    template_name = "books/book_rating_delete_confirmation.html"
    context_object_name = "book_rating"

    def get_success_url(self):
        return reverse_lazy("books:book-detail", kwargs={"pk": self.object.book.pk})


class BookRatingDeleteModalView(LoginRequiredMixin, TemplateView):
    template_name = "books/partials/book_rating_delete_confirmation_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rating"] = get_object_or_404(BookRating, pk=self.kwargs["pk"])
        return context


# Class-based view for the Author autocomplete.
class AuthorAutoCompleteView(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.q:
            return Author.objects.none()

        qs = Author.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


# Class-based view for the Author autocomplete.
class BookAutoCompleteView(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.q:
            return Book.objects.none()

        qs = Book.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs


# API for the books app.


@extend_schema(tags=["Books"])
class BookViewSet(ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="create-from-search")
    def create_from_search(self, request, *args, **kwargs):
        # Custom create method to handle the creation of books with authors
        # It will manage fetching and assigning the authors based on the provided data.
        # The idea is to be able to use it with manual creation and with third party integrations (like google books.)

        # Getting data from the request.
        title = request.data.get("title", "").strip().title()
        authors_names = [
            name.strip()
            for name in request.data.get("authors", "").split(", ")
            if name.strip()
        ]  # list of authors names
        published_date = request.data.get(
            "published_date", ""
        )  # published date from google books api

        # If we have a title and we have a list of authors, we will attempt to create or retrieve the book.
        # If not we should return an error.

        if not (title and authors_names):
            return Response(
                {"error": "Title and authors are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Beging creation/retrieval
        # Collecting or creating Authors from the provided names.

        authors = Author.get_or_create_authors_from_names(authors_names)

        year = parse_year_from_publication_date(published_date)

        # Try to find a book with the same title and authors.

        # We will use the filter_by_authors_and_title method to do this.
        existing_books = Book.filter_by_authors_and_title(title, authors)

        if existing_books.exists():
            book = existing_books.first()
            serializer = self.get_serializer(book)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            # Create the book
            new_book = Book.objects.create(title=title, year=year or None)
            new_book.authors.set(authors)

            # serialize created object
            serializer = self.get_serializer(new_book)
            # Return the created book data.
            return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Book Ratings"])
class BookRatingViewSet(ModelViewSet):
    queryset = BookRating.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return BookRatingCreateSerializer
        elif self.action in ["retrieve", "list"]:
            return BookRatingSerializer
        return BookRatingSerializer

    def get_queryset(self):
        queryset = BookRating.objects.all()

        book_id = self.request.query_params.get("book_id")

        bookrating_filters = dict()

        if book_id:
            bookrating_filters["book_id"] = book_id

        # I need to parse the user_id_list (comma separated) as a list of integers.
        user_id_list = self.request.query_params.get("user_id_list")
        if user_id_list:
            bookrating_filters["user_id__in"] = user_id_list.split(",")

        # Applying filters to the queryset.
        queryset = queryset.filter(**bookrating_filters).order_by("book__title")
        return queryset

    def perform_create(self, serializer):
        # Save the instance using the CreateSerializer
        serializer.save(user=self.request.user)

    @extend_schema(
        request=BookRatingCreateSerializer,
        responses={201: BookRatingSerializer},
    )
    def create(self, request, *args, **kwargs):
        # Use the CreateSerializer for input validation
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)

        # Re-serialize the created instance using the detail serializer
        detail_serializer = BookRatingSerializer(
            create_serializer.instance, context=self.get_serializer_context()
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id_list",
                description="Comma-separated list of user IDs. Example: `1,2,3`",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="book_id",
                description="Filter by book id",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all book ratings, optionally filtered by user or group of users."""
        return super().list(request, *args, **kwargs)
