"""
arXiv module - identifies and resolves arXiv identifiers.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.bibtex import bibtex_string_to_dict


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class ArxivModule(BaseModule):
    """
    Module that handles arXiv ID identification and resolution.
    """

    # arXiv ID patterns from https://info.arxiv.org/help/arxiv_identifier.html
    ARXIV_PATTERNS = [
        r"^\d{4}\.\d{4,5}(v\d+)?$",  # New format: YYMM.NNNNN
        r"^[a-z\-]+(\.[A-Z]{2})?\/\d{7}(v\d+)?$",  # Old format: archive/YYMMNNN
    ]

    def register_hooks(self) -> None:
        """Register hooks for arXiv handling."""
        self._register_hook("identify", self.identify)
        self._register_hook("resolve", self.resolve)
        self._register_hook("before_postprocess_bibtex", self.update_if_doi)
        self._register_hook("before_postprocess_bibtex", self.fix_arxiv_entrytype)

    def identify(self, identifier: str) -> Optional[str]:
        """
        Check if the identifier is an arXiv ID.

        Args:
            identifier: The identifier to check

        Returns:
            "arxiv" if it's an arXiv ID, None otherwise
        """
        if any(re.match(pattern, identifier) for pattern in self.ARXIV_PATTERNS):
            return "arxiv"
        return None

    def resolve(self, identifier_type: str, identifier: str) -> Optional[dict]:
        """
        Resolve an arXiv ID to a BibTeX entry.

        Uses arxiv2bibtex.org to get the BibTeX entry.

        Args:
            identifier_type: Type of identifier (must be "arxiv")
            identifier: The arXiv ID to resolve

        Returns:
            BibTeX dict if resolved, None otherwise
        """
        if identifier_type != "arxiv":
            return None

        # Send a request to arxiv2bibtex.org
        r = requests.get(f"https://arxiv2bibtex.org/?q={identifier}&format=biblatex")

        if r.status_code != 200:
            raise RuntimeError(
                f'Error {r.status_code} resolving arXiv ID "{identifier}"'
            )

        # Find the BibLaTeX entry using BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        textarea = soup.select_one("#biblatex textarea.wikiinfo")

        if textarea is None:
            raise RuntimeError(
                f'Error resolving "{identifier}": no BibTeX entry found'
            )

        bibtex_string = textarea.get_text()

        # Parse the bibstring to a dict
        bibtex_dict = bibtex_string_to_dict(bibtex_string)

        # Optionally fetch abstract from arXiv API
        if self.should_include_abstract() and "abstract" not in bibtex_dict:
            abstract = self._fetch_abstract(identifier)
            if abstract:
                bibtex_dict["abstract"] = abstract

        return bibtex_dict

    def _fetch_abstract(self, arxiv_id: str) -> Optional[str]:
        """
        Fetch abstract from arXiv API.

        Args:
            arxiv_id: The arXiv ID

        Returns:
            Abstract text or None
        """
        try:
            r = requests.get(f"http://export.arxiv.org/api/query?id_list={arxiv_id}")
            if r.status_code != 200:
                return None

            soup = BeautifulSoup(r.text, "xml")
            summary = soup.find("summary")
            if summary:
                return summary.get_text().strip()
        except Exception:
            pass

        return None

    def update_if_doi(self, identifier_type: str, identifier: str, bibtex_dict: dict) -> dict:
        """
        If we resolved an arXiv ID and it has a DOI, optionally resolve
        the DOI instead to get better metadata (published paper vs preprint).

        Args:
            identifier_type: Type of identifier
            identifier: The original identifier
            bibtex_dict: Current BibTeX dict

        Returns:
            Updated BibTeX dict
        """
        if not self.config.update_arxiv_if_doi:
            return bibtex_dict

        if identifier_type != "arxiv":
            return bibtex_dict

        if "doi" not in bibtex_dict:
            return bibtex_dict

        # We have a DOI, resolve it for better metadata
        doi = bibtex_dict["doi"]

        try:
            r = requests.get(
                f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
            )
            if r.status_code == 200:
                new_bibtex_dict = bibtex_string_to_dict(r.text)
                # Keep the arXiv ID reference
                new_bibtex_dict["eprint"] = identifier
                new_bibtex_dict["archiveprefix"] = "arXiv"
                return new_bibtex_dict
        except Exception:
            pass

        return bibtex_dict

    def fix_arxiv_entrytype(self, identifier_type: str, identifier: str, bibtex_dict: dict) -> dict:
      """
      Fix the entry type for arXiv preprints.
      """
      
      if identifier_type != "arxiv":
          return bibtex_dict
      
      if not self.config.fix_arxiv_entrytype:
          return bibtex_dict
      
      bibtex_dict["ENTRYTYPE"] = "article"

      return bibtex_dict