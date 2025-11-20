"""
Methods for resolving identifiers to BibTeX entries.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from typing import List, Dict, Any

from bs4 import BeautifulSoup
import json
import requests


from doi2bibtex.ads import get_ads_token
from doi2bibtex.bibtex import bibtex_string_to_dict, dict_to_bibtex_string
from doi2bibtex.config import Configuration
from doi2bibtex.identify import is_ads_bibcode, is_arxiv_id, is_doi, is_isbn
from doi2bibtex.isbn import resolve_isbn_with_google_api
from doi2bibtex.process import preprocess_identifier, postprocess_bibtex


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def resolve_ads_bibcode(ads_bibcode: str) -> dict:
    """
    Resolve an ADS bibcode using the ADS API and return the BibTeX.
    """

    # Get the ADS token (and raise an error if we don't have one)
    token = get_ads_token(raise_on_error=True)

    # Query the ADS API manually
    r = requests.post(
        url="https://api.adsabs.harvard.edu/v1/export/bibtex",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"bibcode": [ads_bibcode]}),
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


def resolve_arxiv_id(arxiv_id: str) -> dict:
    """
    Resolve an arXiv ID using arxiv2bibtex.org and return the BibTeX
    entry.
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

    return bibtex_dict


def resolve_doi(doi: str) -> dict:
    """
    Resolve a DOI using the Crossref API and return the BibTeX entry.
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
    bibtex = bibtex_string_to_dict(r.text)

    return bibtex


def resolve_identifier(identifier: str, config: Configuration, raise_on_error=False) -> str:
    """
    Resolve the given `identifier` to a BibTeX entry. This function
    basically just determines the type of the identifier, calls the
    appropriate resolver function, and post-processes the result.
    """

    try:

        # Remove the "doi:" or "arXiv:" prefix, if present
        identifier = preprocess_identifier(identifier)

        # Resolve the identifier to a BibTeX entry (as a dict)
        if is_doi(identifier):
            bibtex_dict = resolve_doi(identifier)
        elif is_arxiv_id(identifier):
            bibtex_dict = resolve_arxiv_id(identifier)
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
            bibtex_dict = resolve_doi(identifier)

        # Post-process the BibTeX dict
        bibtex_dict = postprocess_bibtex(bibtex_dict, identifier, config)

        # Convert the BibTeX dict to a string
        return dict_to_bibtex_string(bibtex_dict).strip()

    except Exception as e:
        if raise_on_error :
            raise e
        
        return "\n" + "  There was an error:\n  " + str(e) + "\n"

def resolve_title(title: str, config: Configuration, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers by title using Semantic Scholar API.
    Returns a list of results with title, DOI, authors, year, journal, and abstract.

    To avoid rate limiting, add your API key to ~/.doi2bibtex/config.yaml:
    semantic_scholar_api_key: "your_key_here"

    Get a free API key at: https://www.semanticscholar.org/product/api
    """

    # Query Semantic Scholar API
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": title,
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,externalIds,publicationTypes,publicationVenue"
    }

    # Add API key if available (for higher rate limits)
    headers = {}
    if config.semantic_scholar_api_key:
        headers["x-api-key"] = config.semantic_scholar_api_key

    r = requests.get(url, params=params, headers=headers, timeout=10)

    # Handle rate limiting with better error message
    if r.status_code == 429:
        raise RuntimeError(
            "Semantic Scholar API rate limit exceeded. "
            "Get a free API key at https://www.semanticscholar.org/product/api "
            "and add it to ~/.doi2bibtex/config.yaml with key: semantic_scholar_api_key"
        )

    r.raise_for_status()
    data = r.json()

    results = []
    if "data" in data:
        for item in data["data"]:
            # Get identifier (prefer DOI, fallback to ArXiv)
            external_ids = item.get("externalIds", {})
            identifier = external_ids.get("DOI", "") or external_ids.get("ArXiv", "")

            # Get venue/journal name
            venue = item.get("venue", "")
            if not venue and item.get("publicationVenue"):
                venue = item.get("publicationVenue", {}).get("name", "")

            # Get publisher
            publisher = ""
            if item.get("publicationVenue"):
                publisher = item.get("publicationVenue", {}).get("publisher", "")

            # Get type
            pub_types = item.get("publicationTypes", [])
            pub_type = pub_types[0] if pub_types else ""

            # Transform authors from Semantic Scholar format to CrossRef format
            # Semantic Scholar: [{"name": "John Doe", "authorId": "..."}, ...]
            # CrossRef: [{"given": "John", "family": "Doe"}, ...]
            raw_authors = item.get("authors", [])
            authors = []
            for author in raw_authors:
                name = author.get("name", "")
                if name:
                    # Split name into given and family
                    parts = name.split()
                    if len(parts) > 1:
                        given = " ".join(parts[:-1])
                        family = parts[-1]
                        authors.append({"given": given, "family": family})
                    else:
                        # Single name, treat as family name
                        authors.append({"family": name})

            result = {
                "doi": identifier,
                "title": item.get("title", ""),
                "authors": authors,
                "year": str(item.get("year", "")) if item.get("year") else "",
                "journal": venue,
                "abstract": item.get("abstract", ""),
                "publisher": publisher,
                "type": pub_type
            }

            results.append(result)

    return results

