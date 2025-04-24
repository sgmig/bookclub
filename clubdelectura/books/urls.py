from django.urls import path, include
from books.views import (
    google_books_search,
    BookDetailView,
    BookCreateView,
    BookUpdateView,
    AuthorAutoCompleteView,
    BookViewSet,
    BookSearchView,
    BookSearchViewModule,
)

from rest_framework.routers import DefaultRouter

app_name = "books"

router = DefaultRouter()

router.register("book", BookViewSet, basename="api-book")


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
        "api/",
        include(router.urls),  # Include the API URLs for the BookViewSet
    ),
]
