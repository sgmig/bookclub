from django import forms

from dal import autocomplete

from books.models import Book, BookRating


# TODO: Add languange
class GoogleBooksSearchForm(forms.Form):
    title = forms.CharField(required=False, label="Title")
    author = forms.CharField(required=False, label="Author")

    # isbn = forms.CharField(required=False, label="ISBN")


class BookForm(forms.ModelForm):

    class Meta:
        model = Book
        fields = ["title", "authors", "year"]
        widgets = {
            "authors": autocomplete.ModelSelect2Multiple(
                url="books:author-autocomplete",
                attrs={
                    "data-placeholder": "Search for an author",
                },
            )
        }

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title:
            raise forms.ValidationError("Title is required.")
        return title.title()


class BookRatingForm(forms.ModelForm):

    class Meta:
        model = BookRating
        fields = ["book", "rating", "comment"]
        widgets = {
            "book": autocomplete.ModelSelect2(
                url="books:book-autocomplete",
                attrs={
                    "data-placeholder": "Search for a title",
                },
            ),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super().__init__(*args, **kwargs)

        if book:
            self.fields["book"].initial = book
            # self.fields["book"].disabled = True
