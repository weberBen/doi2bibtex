"""
DOI module - identifies and resolves DOI identifiers.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import re
from typing import Optional

import requests

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.bibtex import bibtex_string_to_dict


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class DoiModule(BaseModule):
    """
    Module that handles DOI identification and resolution.
    """

    # DOI patterns from https://www.crossref.org/blog/dois-and-matching-regular-expressions
    DOI_PATTERNS = [
        r"^10.\d{4,9}/[-.;()/:\w]+$",
        r"^10.1002/[^\s]+$",
        r"^10.\d{4}/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d$",
        r"^10.1021/\w\w\d+$",
        r"^10.1207/[\w\d]+\&\d+_\d+$",
    ]

    def register_hooks(self) -> None:
        """Register hooks for DOI handling."""
        self._register_hook("identify", self.identify)
        self._register_hook("resolve", self.resolve)

    def identify(self, identifier: str) -> Optional[str]:
        """
        Check if the identifier is a DOI.

        Args:
            identifier: The identifier to check

        Returns:
            "doi" if it's a DOI, None otherwise
        """
        if any(re.match(pattern, identifier) for pattern in self.DOI_PATTERNS):
            return "doi"
        return None

    def resolve(self, identifier_type: str, identifier: str) -> Optional[dict]:
        """
        Resolve a DOI to a BibTeX entry.

        Args:
            identifier_type: Type of identifier (must be "doi")
            identifier: The DOI to resolve

        Returns:
            BibTeX dict if resolved, None otherwise
        """
        if identifier_type != "doi":
            return None

        # Send a request to the Crossref API
        r = requests.get(
            f"https://api.crossref.org/works/{identifier}/transform/application/x-bibtex"
        )

        if r.status_code != 200:
            raise RuntimeError(
                f'Error {r.status_code} resolving DOI "{identifier}": no BibTeX entry found'
            )

        # Parse the response into a dict
        bibtex_dict = bibtex_string_to_dict(r.text)

        return bibtex_dict
