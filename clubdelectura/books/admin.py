from django.contrib import admin

from books.models import Author, Book, BookRating

# Register your models here.


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):

    list_display = ["name"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):

    list_display = ["title", "_list_authors", "year"]
    search_fields = ["title", "authors__name"]
    ordering = ["title"]

    def _list_authors(self, obj):
        return obj.list_authors()

    _list_authors.short_description = "Authors"


@admin.register(BookRating)
class BookRatingAdmin(admin.ModelAdmin):
    list_display = ["book", "user", "rating", "created_at"]
    search_fields = ["book__title", "user__username"]
    ordering = ["created_at"]
