from django.urls import path, include
from books.views import (
    google_books_search,
    BookDetailView,
    BookCreateView,
    BookUpdateView,
    AuthorAutoCompleteView,
    BookAutoCompleteView,
    BookSearchView,
    BookSearchViewModule,
    BookRatingDeleteView,
    BookRatingDeleteModalView,
    BookRatingListView,
    BookRatingUpdateView,
    BookViewSet,
    BookRatingViewSet,
)

from rest_framework.routers import DefaultRouter

app_name = "books"

router = DefaultRouter()

router.register("book", BookViewSet, basename="api-book")
router.register("book-rating", BookRatingViewSet, basename="api-book-rating")


urlpatterns = [
    path("search-books/", BookSearchView.as_view(), name="google-books-search"),
    path(
        "search-books-module/",
        BookSearchViewModule.as_view(),
        name="google-books-search-module",
    ),
    path("create-book/", BookCreateView.as_view(), name="create-book"),
    path("<int:pk>/", BookDetailView.as_view(), name="book-detail"),
    path("update/<int:pk>/", BookUpdateView.as_view(), name="update-book"),
    path(
        "autocomplete/",
        BookAutoCompleteView.as_view(),
        name="book-autocomplete",
    ),
    path("book-ratings/", BookRatingListView.as_view(), name="book-rating-list"),
    path(
        "book-rating/<int:pk>/update/",
        BookRatingUpdateView.as_view(),
        name="book-rating-update",
    ),
    path(
        "book-rating/<int:pk>/delete/",
        BookRatingDeleteView.as_view(),
        name="book-rating-delete",
    ),
    path(
        "book-rating/<int:pk>/delete-modal/",
        BookRatingDeleteModalView.as_view(),
        name="book-rating-delete-modal",
    ),
    path(
        "author/autocomplete/",
        AuthorAutoCompleteView.as_view(),
        name="author-autocomplete",
    ),
    path(
        "api/",
        include(router.urls),  # Include the API URLs for the BookViewSet
    ),
]
