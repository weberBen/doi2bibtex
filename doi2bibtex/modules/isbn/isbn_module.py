"""
ISBN module - identifies and resolves ISBN identifiers.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json
from typing import Optional

import requests
from isbnlib import is_isbn10, is_isbn13

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.process import generate_citekey


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class IsbnModule(BaseModule):
    """
    Module that handles ISBN identification and resolution.
    """

    def register_hooks(self) -> None:
        """Register hooks for ISBN handling."""
        self._register_hook("identify", self.identify)
        self._register_hook("resolve", self.resolve)

    def identify(self, identifier: str) -> Optional[str]:
        """
        Check if the identifier is an ISBN.

        Args:
            identifier: The identifier to check

        Returns:
            "isbn" if it's an ISBN, None otherwise
        """
        if bool(is_isbn10(identifier)) or bool(is_isbn13(identifier)):
            return "isbn"
        return None

    def resolve(self, identifier_type: str, identifier: str) -> Optional[dict]:
        """
        Resolve an ISBN to a BibTeX entry using Google Books API.

        Args:
            identifier_type: Type of identifier (must be "isbn")
            identifier: The ISBN to resolve

        Returns:
            BibTeX dict if resolved, None otherwise
        """
        if identifier_type != "isbn":
            return None

        # Remove dashes from ISBN for more reliable lookup
        query = identifier.replace("-", "")

        # Query the Google Books API
        r = requests.get(
            url=f"https://www.googleapis.com/books/v1/volumes?q=isbn:{query}",
            headers={"Accept": "application/json"},
        )

        if r.status_code != 200:
            raise RuntimeError(
                f'Error {r.status_code} resolving ISBN "{identifier}": no BibTeX entry found'
            )

        # Parse the response
        response = json.loads(r.text)

        # Check if we got any results
        items = response.get("items", [])
        if not items:
            raise RuntimeError(
                f'Error resolving ISBN "{identifier}": no BibTeX entry found'
            )

        # Get the first item
        item = items[0]
        volume_info = item.get("volumeInfo", {})

        title = volume_info.get("title", "")
        subtitle = volume_info.get("subtitle", "")

        # Construct a BibTeX entry
        bibtex_dict = {
            "ENTRYTYPE": "book",
            "ID": identifier,
            "author": " and ".join(volume_info.get("authors", [])),
            "title": title + ((": " + subtitle) if subtitle else ""),
            "publisher": volume_info.get("publisher", ""),
            "year": volume_info.get("publishedDate", "")[:4],
            "isbn": identifier,
        }

        # Generate citekey
        bibtex_dict = generate_citekey(bibtex_dict)

        return bibtex_dict
