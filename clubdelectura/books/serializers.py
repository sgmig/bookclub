from rest_framework import serializers

from books.models import Book, Author


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
