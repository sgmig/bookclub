import requests
from datetime import datetime

from django.conf import settings

from django.db.models import Count

from django.shortcuts import render, redirect
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


# django autocomplete-light
from dal import autocomplete

from books.models import Book, Author, BookRating
from books.forms import GoogleBooksSearchForm, BookForm
from books.serializers import BookSerializer
from books.integrations.google_books import (
    GoogleBooksAPI,
    parse_year_from_publication_date,
)

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


class BookRatingDeleteView(DeleteView):
    model = BookRating
    template_name = "books/book_rating_delete_confirmation.html"
    context_object_name = "book_rating"

    def get_success_url(self):
        return reverse_lazy("books:book-detail", kwargs={"pk": self.object.book.pk})


# Class-based view for the Author autocomplete.
class AuthorAutoCompleteView(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.q:
            return Author.objects.none()

        qs = Author.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


# API for the books app.


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
