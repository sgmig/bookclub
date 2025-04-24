# A set of utilities to interact with the Google Books API

import requests

from datetime import datetime

from django.conf import settings


class GoogleBooksAPI:
    def __init__(self, max_results=10):
        self.api_key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
        self.api_volumes_url = getattr(settings, "GOOGLE_BOOKS_API_URL", "")
        self.max_results = max_results
        self.volume_query_fields = {
            "title": "intitle",
            "author": "inauthor",
            "publisher": "inpublisher",
            "subject": "subject",
            "isbn": "isbn",
            "lccn": "lccn",
            "oclc": "oclc",
        }

    def search_volumes(self, **search_terms):
        """
        Search for books using the Google Books API.

        Args:
            **search_terms: Search parameters like title, author, isbn, etc.

        Returns:
            dict: JSON response from Google Books API if successful, else empty dict.

        Reference:
            https://developers.google.com/books/docs/v1/using
        """
        query_segments = [
            f"{api_prefix}:{search_terms[param]}"
            for param, api_prefix in self.volume_query_fields.items()
            if search_terms.get(param)
        ]

        query_string = "+".join(query_segments)

        if not self.api_volumes_url or not self.api_key or not query_string:
            return {}

        response = requests.get(
            self.api_volumes_url,
            params={
                "q": query_string,
                "maxResults": search_terms.get("max_results", self.max_results),
                "key": self.api_key,
            },
        )

        if response.status_code == 200:
            return response

        return {}


def parse_year_from_publication_date(date_str):
    """
    Parse the publication date from the Google Books API.

    Args:
        date_str (str): The publication date string from the API.

        Examples: "2023-10-01", "2023-10", "2023"

    Returns:
        int: The year of publication or None if not found.
    """

    full_date_format = "%Y-%m-%d"
    year_month_format = "%Y-%m"
    year_format = "%Y"

    date = None

    # I don't care about the time or timezone info, so I truncate it.
    if len(date_str) >= 10:
        print(date_str)
        print(f"truncate to {date_str[:10]} ")
        date = datetime.strptime(date_str[:10], full_date_format)
    elif len(date_str) == 7:
        date = datetime.strptime(date_str, year_month_format)
    elif len(date_str) == 4:
        date = datetime.strptime(date_str, year_format)

    year = date.year if date else None

    return year
