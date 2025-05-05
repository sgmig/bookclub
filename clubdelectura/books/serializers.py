from rest_framework import serializers
from django.contrib.auth import get_user_model

from books.models import Book, Author, BookRating

# Get the user model. Used in ratings.
User = get_user_model()


# Author serializer
class AuthorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Author
        fields = ["id", "name"]


# Books serializer
class BookSerializer(serializers.ModelSerializer):

    authors = serializers.StringRelatedField(many=True)

    class Meta:
        model = Book
        fields = ["id", "title", "authors", "year"]


class BookRatingCreateSerializer(serializers.ModelSerializer):
    """Serializer for BookRating model used in Creation."""

    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = BookRating
        fields = ["book", "rating", "comment"]


class BookRatingSerializer(serializers.ModelSerializer):
    """Serializer for BookRating model. Used in list views and detail views, including book informamation."""

    book = BookSerializer()
    user = serializers.StringRelatedField()

    class Meta:
        model = BookRating
        fields = ["id", "book", "user", "rating", "comment", "created_at"]
