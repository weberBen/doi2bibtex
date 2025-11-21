"""
Methods for searching papers by title using various APIs.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

import requests

from doi2bibtex.config import Configuration


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def search_openalex(title: str, config: Configuration, limit: int = 10) -> List[Dict[str, Any]]:
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


def search_crossref(title: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers by title using CrossRef API.
    Returns a list of results with title, DOI, authors, year, journal, and abstract.

    CrossRef API: https://api.crossref.org
    Rate limit: 50 requests/second, no API key required
    """

    # Query CrossRef API
    url = "https://api.crossref.org/works"
    params = {
        "query.title": title,
        "rows": limit,
        "select": "DOI,title,author,published,container-title,abstract,publisher,type"
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    if "message" in data and "items" in data["message"]:
        for item in data["message"]["items"]:
            result = {
                "doi": item.get("DOI", ""),
                "title": item.get("title", [""])[0] if item.get("title") else "",
                "authors": item.get("author", []),  # CrossRef format already correct
                "year": "",
                "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
                "abstract": item.get("abstract", ""),
                "publisher": item.get("publisher", ""),
                "type": item.get("type", "")
            }

            # Extract year from published date
            if "published" in item:
                date_parts = item["published"].get("date-parts", [[]])[0]
                if date_parts:
                    result["year"] = str(date_parts[0])

            results.append(result)

    return results


def search_semanticscholar(title: str, config: Configuration, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers by title using Semantic Scholar API.
    Returns a list of results with title, DOI, authors, year, journal, and abstract.

    Add API key to ~/.doi2bibtex/config.yaml for higher rate limits:
    semantic_scholar_api_key: "your_key_here"

    Semantic Scholar API: https://www.semanticscholar.org/product/api
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

    # Handle rate limiting
    if r.status_code == 429:
        return []  # Return empty if rate limited

    r.raise_for_status()
    data = r.json()

    results = []
    if "data" in data:
        for item in data["data"]:
            # Get identifier (prefer DOI, fallback to ArXiv)
            external_ids = item.get("externalIds", {})
            identifier = external_ids.get("DOI", "") or external_ids.get("ArXiv", "")

            if identifier and "arxiv." in identifier.lower():
                arxiv_identifier = identifier.split(".")
                identifier = f'{arxiv_identifier[-2]}.{arxiv_identifier[-1]}'

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


def _add_source_to_results(results: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    """Add source field to all results"""
    for result in results:
        result["source"] = source
    return results


def _deduplicate_by_doi(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate results by DOI, keeping first occurrence"""
    seen_dois = set()
    deduplicated = []

    for result in results:
        doi = result.get("doi", "")
        # If no DOI or DOI not seen yet, keep it
        if not doi or doi not in seen_dois:
            deduplicated.append(result)
            if doi:
                seen_dois.add(doi)

    return deduplicated


def _interleave_results(results_by_source: Dict[str, List[Dict[str, Any]]], limit: int) -> List[Dict[str, Any]]:
    """Interleave results from multiple sources (1st from each, 2nd from each, etc.)"""
    interleaved = []
    max_len = max(len(r) for r in results_by_source.values()) if results_by_source else 0

    for i in range(max_len):
        for source_results in results_by_source.values():
            if i < len(source_results):
                interleaved.append(source_results[i])
                if len(interleaved) >= limit:
                    return interleaved

    return interleaved


def search_papers(title: str, config: Configuration, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers by title using configured sources.

    Modes:
    - Sequential (merge_search_results=False): Try sources in order until results found
    - Parallel (merge_search_results=True): Query all sources in parallel and interleave results

    Args:
        title: Paper title to search for
        config: Configuration object
        limit: Maximum number of results

    Returns:
        List of paper results with unified format including source field
    """

    # Map source names to search functions
    search_functions = {
        "openalex": lambda: _add_source_to_results(search_openalex(title, config, limit), "openalex"),
        "crossref": lambda: _add_source_to_results(search_crossref(title, limit), "crossref"),
        "semanticscholar": lambda: _add_source_to_results(search_semanticscholar(title, config, limit), "semanticscholar"),
    }

    # Filter enabled sources
    enabled_sources = [s for s in config.search_sources if s in search_functions]

    if not enabled_sources:
        # Default to openalex if no valid sources
        enabled_sources = ["openalex"]

    # Sequential mode: try sources in order
    if not config.merge_search_results:
        for source in enabled_sources:
            results = search_functions[source]()
            if results:
                return results
        return []

    # Parallel mode: query all sources and interleave
    results_by_source = {}

    with ThreadPoolExecutor(max_workers=len(enabled_sources)) as executor:
        # Submit all searches
        future_to_source = {
            executor.submit(search_functions[source]): source
            for source in enabled_sources
        }

        # Collect results as they complete
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                results = future.result()
                if results:
                    results_by_source[source] = results
            except Exception:
                # Skip sources that error
                pass

    # Interleave results
    interleaved = _interleave_results(results_by_source, limit)

    # Deduplicate by DOI
    deduplicated = _deduplicate_by_doi(interleaved)

    return deduplicated
