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
    Search for papers by title using OpenAlex API.
    Returns a list of results with title, DOI, authors, year, journal, and abstract.

    Optionally add your email to ~/.doi2bibtex/config.yaml for polite pool (faster):
    openalex_email: "your@email.com"

    OpenAlex API: https://docs.openalex.org
    Rate limit: 100,000 requests/day, no API key required
    """

    # Query OpenAlex API
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"title.search:{title}",
        "per_page": limit,
    }

    # Add email for polite pool (recommended for better rate limits)
    if config.openalex_email:
        params["mailto"] = config.openalex_email

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    if "results" in data:
        for item in data["results"]:
            # Get identifier (prefer DOI, fallback to ArXiv)
            ids = item.get("ids", {})
            doi = ids.get("doi", "")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")

            # Try to extract arXiv ID from OpenAlex ID or other fields
            arxiv_id = ""
            openalex_id = ids.get("openalex", "")
            if "arxiv" in openalex_id.lower():
                # Extract arXiv ID from OpenAlex ID if present
                arxiv_id = openalex_id.split("/")[-1]

            identifier = doi or arxiv_id

            # Handle arXiv DOIs
            if identifier and "arxiv." in identifier.lower():
                arxiv_identifier = identifier.split(".")
                identifier = f'{arxiv_identifier[-2]}.{arxiv_identifier[-1]}'

            # Get venue/journal name from primary_location
            venue = ""
            primary_location = item.get("primary_location", {})
            if primary_location and primary_location.get("source"):
                venue = primary_location.get("source", {}).get("display_name", "")

            # Get publisher
            publisher = ""
            if primary_location and primary_location.get("source"):
                publisher = primary_location.get("source", {}).get("host_organization_name", "")

            # Get type
            pub_type = item.get("type", "")

            # Transform authors from OpenAlex format to CrossRef format
            # OpenAlex: [{"author": {"display_name": "John Doe"}}, ...]
            # CrossRef: [{"given": "John", "family": "Doe"}, ...]
            raw_authorships = item.get("authorships", [])
            authors = []
            for authorship in raw_authorships:
                author_obj = authorship.get("author", {})
                name = author_obj.get("display_name", "")
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

            # Get year
            year = item.get("publication_year", "")

            # Abstract: OpenAlex uses inverted index format, reconstruct it
            abstract = ""
            abstract_inv = item.get("abstract_inverted_index", {})
            if abstract_inv:
                # Find max position to create array
                max_pos = 0
                for positions in abstract_inv.values():
                    if positions:
                        max_pos = max(max_pos, max(positions))

                # Create word array and fill it
                words = [""] * (max_pos + 1)
                for word, positions in abstract_inv.items():
                    for pos in positions:
                        words[pos] = word

                # Join words
                abstract = " ".join(words)

            result = {
                "doi": identifier,
                "title": item.get("title", ""),
                "authors": authors,
                "year": str(year) if year else "",
                "journal": venue,
                "abstract": abstract,
                "publisher": publisher,
                "type": pub_type
            }

            results.append(result)

    return results

