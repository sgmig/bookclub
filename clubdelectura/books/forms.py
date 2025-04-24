from django import forms

from dal import autocomplete

from books.models import Book


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
