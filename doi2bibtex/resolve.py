"""
Methods for resolving identifiers to BibTeX entries.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from bs4 import BeautifulSoup

import json
import xml.etree.ElementTree as ET

import requests

from doi2bibtex.ads import get_ads_token
from doi2bibtex.bibtex import bibtex_string_to_dict, dict_to_bibtex_string
from doi2bibtex.config import Configuration
from doi2bibtex.identify import is_ads_bibcode, is_arxiv_id, is_doi, is_isbn
from doi2bibtex.isbn import resolve_isbn_with_google_api
from doi2bibtex.process import preprocess_identifier, postprocess_bibtex
from doi2bibtex.utils import unescape_text


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def resolve_ads_bibcode(ads_bibcode: str) -> dict:
    """
    Resolve an ADS bibcode using the ADS API and return the BibTeX with abstract.
    Uses /bibtexabs endpoint to include abstracts and all authors.
    """

    # Get the ADS token (and raise an error if we don't have one)
    token = get_ads_token(raise_on_error=True)

    # Query the ADS API manually using bibtexabs to include abstract
    r = requests.post(
        url="https://api.adsabs.harvard.edu/v1/export/bibtexabs",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "bibcode": [ads_bibcode],
            "maxauthor": 0  # 0 = all authors
        }),
    )

    # Check if we got a 200 response; if not, raise an error
    if (error := r.status_code) != 200:
        raise RuntimeError(
            f'Error {error} resolving "{ads_bibcode}": no BibTeX entry found'
        )

    # Parse the response using JSON
    bibtex_string = json.loads(r.text)["export"]

    # Parse the bibstring to a dict
    bibtex_dict = bibtex_string_to_dict(bibtex_string)

    return bibtex_dict

def resolve_arxiv_abstract(arxiv_id: str) -> dict:
    # Fetch abstract from arXiv API
    
    arxiv_api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    r_arxiv = requests.get(arxiv_api_url, timeout=10)
    r_arxiv.raise_for_status()

    # Parse XML response
    root = ET.fromstring(r_arxiv.text)
    # Define namespace for arXiv API
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    # Extract abstract (called 'summary' in arXiv API)
    summary_elem = root.find('.//atom:entry/atom:summary', ns)
    if summary_elem is not None and summary_elem.text:
        abstract = summary_elem.text.strip()
        # Clean up the abstract (remove extra whitespace)
        abstract = ' '.join(abstract.split())
        return unescape_text(abstract)
    
    return ""


def resolve_arxiv_id(arxiv_id: str, fetchAbstract: bool = False) -> dict:
    """
    Resolve an arXiv ID using arxiv2bibtex.org and return the BibTeX
    entry with abstract from arXiv API.
    """

    # Send a request to arxiv2bibtex.org
    # We could also use the arXiv API instead, but it's a bit more complicated
    # and would require us to parse the XML response ourselves...
    r = requests.get(f"https://arxiv2bibtex.org/?q={arxiv_id}&format=biblatex")
    if (error := r.status_code) != 200:
        raise RuntimeError(f"Error {error} resolving {arxiv_id}")

    # Find the BibLaTeX entry using BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    textarea = soup.select_one("#biblatex textarea.wikiinfo")
    if textarea is None:
        raise RuntimeError(
            f'Error resolving "{arxiv_id}": no BibTeX entry found'
        )
    bibtex_string = textarea.get_text()

    # Parse the bibstring to a dict
    bibtex_dict = bibtex_string_to_dict(bibtex_string)

    if fetchAbstract:
        bibtex_dict["abstract"] = resolve_arxiv_abstract(arxiv_id)

    return bibtex_dict


def resolve_abstract_doi(doi: str) -> dict:
    # Fetch abstract from CrossRef metadata API
    metadata_url = f"https://api.crossref.org/works/{doi}"
    r_metadata = requests.get(metadata_url, timeout=10)
    r_metadata.raise_for_status()

    data = r_metadata.json()
    if "message" in data and "abstract" in data["message"]:
        abstract = data["message"]["abstract"]
        if abstract:
            return unescape_text(abstract)

    return ""

def resolve_doi(doi: str, fetchAbstract: bool = False) -> dict:
    """
    Resolve a DOI using the Crossref API and return the BibTeX entry
    """

    # Send a request to the Crossref API to get the BibTeX entry
    r = requests.get(
        f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
    )
    if (error := r.status_code) != 200:
        raise RuntimeError(
            f'Error {error} resolving DOI "{doi}": no BibTeX entry found'
        )

    # Parse the response into a dict
    bibtex_dict = bibtex_string_to_dict(r.text)

    if fetchAbstract:
        bibtex_dict["abstract"] = resolve_abstract_doi(doi)

    return bibtex_dict


def resolve_identifier(identifier: str, config: Configuration) -> str:
    """
    Resolve the given `identifier` to a BibTeX entry. This function
    basically just determines the type of the identifier, calls the
    appropriate resolver function, and post-processes the result.
    """

    showAbstract = "abstract" not in config.remove_fields["all"]
    try:

        # Remove the "doi:" or "arXiv:" prefix, if present
        identifier = preprocess_identifier(identifier)

        # Resolve the identifier to a BibTeX entry (as a dict)
        if is_doi(identifier):
            bibtex_dict = resolve_doi(identifier, fetchAbstract=showAbstract)
        elif is_arxiv_id(identifier):
            bibtex_dict = resolve_arxiv_id(identifier, fetchAbstract=showAbstract)
        elif is_ads_bibcode(identifier):
            bibtex_dict = resolve_ads_bibcode(identifier)
        elif is_isbn(identifier):
            bibtex_dict = resolve_isbn_with_google_api(identifier)
        else:
            raise RuntimeError(f"Unrecognized identifier: {identifier}")

        # If we resolved an arXiv ID and we got a BibTeX entry with a DOI,
        # we can update the identifier to the DOI and resolve that one to
        # get a better BibTeX entry (published paper instead of preprint)
        if (
            config.update_arxiv_if_doi and
            is_arxiv_id(identifier) and
            "doi" in bibtex_dict
        ):
            identifier = bibtex_dict["doi"]
            bibtex_dict = resolve_doi(identifier, fetchAbstract=showAbstract)

        # Post-process the BibTeX dict
        bibtex_dict = postprocess_bibtex(bibtex_dict, identifier, config)

        # Convert the BibTeX dict to a string
        return dict_to_bibtex_string(bibtex_dict).strip()

    except Exception as e:
        return "\n" + "  There was an error:\n  " + str(e) + "\n"
