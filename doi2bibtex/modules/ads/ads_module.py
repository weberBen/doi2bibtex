"""
ADS module - identifies and resolves NASA/ADS bibcodes.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.bibtex import bibtex_string_to_dict


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class AdsModule(BaseModule):
    """
    Module that handles ADS bibcode identification and resolution.
    """

    # ADS bibcode pattern (format: YYYYJJJJJVVVVMPPPPA)
    # See: https://ui.adsabs.harvard.edu/help/actions/bibcode
    ADS_PATTERN = re.compile(
        r"^"
        r"(?P<YYYY>\d{4})"
        r"(?P<JJJJJ>[\w\.\&]{5})"
        r"(?P<VVVV>[\w\.]{4})"
        r"(?P<M>\S)"
        r"(?P<PPPP>[\d\.]{4})"
        r"(?P<A>[A-Z])"
        r"$"
    )

    def register_hooks(self) -> None:
        """Register hooks for ADS handling."""
        self._register_hook("identify", self.identify)
        self._register_hook("resolve", self.resolve)
        self._register_hook("after_postprocess_bibtex", self.add_adsurl_to_bibtex)

    def identify(self, identifier: str) -> Optional[str]:
        """
        Check if the given `identifier` is an ADS bibcode.
        """
        is_ads = self.ADS_PATTERN.match(identifier) is not None
        return "ads" if is_ads else None

    def resolve(self, identifier_type: str, identifier: str) -> Optional[dict]:
        """
        Resolve an ADS bibcode to a BibTeX entry.

        Args:
            identifier_type: Type of identifier (must be "ads")
            identifier: The ADS bibcode to resolve

        Returns:
            BibTeX dict if resolved, None otherwise
        """
        if identifier_type != "ads":
            return None

        # Get the ADS token (raises error if not found)
        token = self.get_ads_token(raise_on_error=True)

        # Query the ADS API
        r = requests.post(
            url="https://api.adsabs.harvard.edu/v1/export/bibtex",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            data=json.dumps({"bibcode": [identifier]}),
        )

        if r.status_code != 200:
            raise RuntimeError(
                f'Error {r.status_code} resolving ADS bibcode "{identifier}": no BibTeX entry found'
            )

        # Parse the response
        bibtex_string = json.loads(r.text)["export"]

        # Parse the bibstring to a dict
        bibtex_dict = bibtex_string_to_dict(bibtex_string)

        return bibtex_dict

    def get_ads_token(self, raise_on_error: bool = False) -> Optional[str]:
        """
        Get the ADS API token from an environment variable or a file.
        If `raise_on_error` is True, raise an error if no token is found.
        """
        # Try to get the ADS token from an environment variable
        if (token := os.environ.get("ADS_TOKEN")) is not None:
            return token

        # Try to get the ADS token from a file
        file_path = Path.home() / ".doi2bibtex" / "ads_token"
        if file_path.exists():
            with open(file_path, "r") as f:
                return f.read().strip()

        # If we get here, we didn't find a token
        if raise_on_error:
            raise RuntimeError(
                "No ADS token found! Please set the ADS_TOKEN environment "
                "variable, or create a file at ~/.doi2bibtex/ads_token "
                "containing your ADS token."
            )

        return None

    def get_ads_bibcode_for_identifier(self, identifier: str) -> str:
        """
        Query ADS for the given `identifier` and return the bibcode of the
        matching result (or an empty string, if no results are found).
        """
        # Get the ADS token (and raise an error if we don't have one)
        token = self.get_ads_token(raise_on_error=True)

        # Query the ADS API manually
        q = urlencode({"identifier": identifier})
        q = q.replace("identifier=", "identifier:")
        fl = "bibcode,identifier"
        r = requests.get(
            url=f"https://api.adsabs.harvard.edu/v1/search/query?q={q}&fl={fl}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        # Check if we got a 200 response
        if r.status_code != 200:
            return ""

        # Parse the response using JSON
        response = json.loads(r.text)["response"]

        # Find the result that matches the identifier
        for result in response["docs"]:
            if any(identifier.lower() in _.lower() for _ in result["identifier"]):
                return str(result["bibcode"])

        # If we get here, we didn't find a match
        return ""

    def add_adsurl_to_bibtex(
        self,
        identifier_type: str,
        identifier: str,
        bibtex_dict: dict
    ) -> dict:
        """
        Resolve the `adsurl` field for a given BibTeX entry.
        """
        # Check if resolve_adsurl is enabled
        if not self.config.resolve_adsurl:
            return bibtex_dict

        # If the entry already has an `adsurl` field, return the original dict
        if "adsurl" in bibtex_dict:
            return bibtex_dict

        # Try to resolve the ADS bibcode
        try:
            bibcode = self.get_ads_bibcode_for_identifier(identifier)

            # If we found a bibcode, construct the ADS URL and add it to the dict
            if bibcode:
                bibtex_dict["adsurl"] = f"https://adsabs.harvard.edu/abs/{bibcode}"
        except Exception:
            # If we fail to resolve ADS URL, just skip it
            pass

        return bibtex_dict
