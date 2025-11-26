"""
Methods for resolving identifiers to BibTeX entries.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from doi2bibtex.bibtex import dict_to_bibtex_string
from doi2bibtex.config import Configuration
from doi2bibtex.hooks import hooks
from doi2bibtex.process import preprocess_identifier, postprocess_bibtex


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def resolve_identifier(identifier: str, config: Configuration) -> str:
    """
    Resolve the given `identifier` to a BibTeX entry.

    This function:
    1. Preprocesses the identifier (removes prefixes like "doi:", "arXiv:")
    2. Identifies the type using registered identify hooks
    3. Resolves to BibTeX using registered resolve hooks
    4. Runs before/after postprocess hooks
    5. Postprocesses the BibTeX entry
    6. Returns the formatted BibTeX string

    Args:
        identifier: The identifier to resolve (DOI, arXiv ID, ISBN, ADS bibcode)
        config: The configuration object

    Returns:
        The BibTeX entry as a formatted string
    """
    try:
        # Remove prefixes like "doi:" or "arXiv:"
        identifier = preprocess_identifier(identifier)

        # Identify the type of identifier using hooks
        identifier_type = None
        for hook in hooks["identify"]:
            identifier_type = hook(identifier)
            if identifier_type:
                break

        if not identifier_type:
            raise RuntimeError(f"Unrecognized identifier: {identifier}")

        # Resolve the identifier to a BibTeX dict using hooks
        bibtex_dict = None
        for hook in hooks["resolve"]:
            bibtex_dict = hook(identifier_type, identifier)
            if bibtex_dict:
                break

        if not bibtex_dict:
            raise RuntimeError(f"Could not resolve identifier: {identifier}")

        # Run before_postprocess hooks
        for hook in hooks["before_postprocess_bibtex"]:
            bibtex_dict = hook(identifier_type, identifier, bibtex_dict)

        # Postprocess the BibTeX dict
        bibtex_dict = postprocess_bibtex(bibtex_dict, identifier, config)

        # Run after_postprocess hooks
        for hook in hooks["after_postprocess_bibtex"]:
            bibtex_dict = hook(identifier_type, identifier, bibtex_dict)

        # Convert the BibTeX dict to a string
        return dict_to_bibtex_string(bibtex_dict).strip()

    except Exception as e:
        return "\n" + "  There was an error:\n  " + str(e) + "\n"
