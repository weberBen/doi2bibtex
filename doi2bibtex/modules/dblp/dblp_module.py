"""
DBLP module - cross-matches entries with dblp.org for venue information.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json
from typing import Optional

import requests
from bibtexparser.customization import splitname

from doi2bibtex.modules.base import BaseModule


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class DblpModule(BaseModule):
    """
    Module that cross-matches BibTeX entries with dblp.org to add
    venue information for conference papers.
    """

    def register_hooks(self) -> None:
        """Register hooks for DBLP handling."""
        self._register_hook("after_postprocess_bibtex", self.crossmatch_with_dblp)

    def crossmatch_with_dblp(
        self,
        identifier_type: str,
        identifier: str,
        bibtex_dict: dict
    ) -> dict:
        """
        Cross-match the given BibTeX entry with the dblp database to check
        if there is a matching conference paper. If so, add the venue and
        year of the conference paper to the BibTeX entry.

        Note: This function usually only makes sense for arXiv preprints.
        """
        # Check if crossmatch is enabled in config
        if not self.config.crossmatch_with_dblp:
            return bibtex_dict

        # If we do not have a title and author, we cannot cross-match with dblp
        if "title" not in bibtex_dict or "author" not in bibtex_dict:
            return bibtex_dict

        # Extract the title and first author from the BibTeX entry
        title = bibtex_dict["title"]
        author = splitname(bibtex_dict["author"].split(" and ")[0])

        # Construct query and make request to the dblp API
        query = "+".join(author["last"]) + "+" + title.replace(" ", "+")
        url = f"https://dblp.org/search/publ/api?q={query}&format=json&h=1000"

        try:
            # Check if the request was successful
            r = requests.get(url)
            if r.status_code != 200:
                return bibtex_dict

            # Parse the response as JSON and extract the papers
            data = dict(json.loads(r.text))
            if "hit" not in data["result"]["hits"]:
                return bibtex_dict
            papers = data["result"]["hits"]["hit"]

            # Find the paper in the list of papers
            info = {}
            for paper in papers:
                paper_info = dict(paper["info"])
                if (
                    "type" in paper_info
                    and paper_info["type"] == "Conference and Workshop Papers"
                ) and (
                    ("title" in paper_info and title == paper_info["title"][:-1])
                    or ("ee" in paper_info and identifier in paper_info["ee"])
                    or ("volume" in paper_info and identifier in paper_info["volume"])
                ):
                    info = paper_info
                    break

            # Add the venue information from dblp to the BibTeX entry
            if info and "venue" in info and "year" in info:
                bibtex_dict["addendum"] = (
                    bibtex_dict.get("addendum", "")
                    + " "
                    + f"Published at {info['venue']}~{info['year']}."
                ).strip()

        except Exception:
            # If anything goes wrong, just return the original dict
            pass

        return bibtex_dict
