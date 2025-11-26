"""
Public API for doi2bibtex modules.

This module exposes all the utilities and functions that modules
(both built-in and custom) can use. Custom modules should import from here:

    from doi2bibtex.api import BaseModule, bibtex_string_to_dict, ...

This avoids circular imports and provides a stable API.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# Re-export everything that modules might need

# Bibtex utilities
from doi2bibtex.bibtex import (
    bibtex_string_to_dict,
    dict_to_bibtex_string,
)

# Processing utilities
from doi2bibtex.process import (
    preprocess_identifier,
    postprocess_bibtex,
    generate_citekey,
)

# General utilities
from doi2bibtex.utils import (
    doi_to_url,
    latex_to_unicode,
    remove_accented_characters,
)

# Configuration
from doi2bibtex.config import Configuration

# Hooks system
from doi2bibtex.hooks import register_hook, hooks

# Base module class
from doi2bibtex.modules.base import BaseModule


# -----------------------------------------------------------------------------
# MODULE API
# -----------------------------------------------------------------------------

__all__ = [
    # Bibtex
    "bibtex_string_to_dict",
    "dict_to_bibtex_string",
    # Process
    "preprocess_identifier",
    "postprocess_bibtex",
    "generate_citekey",
    "is_arxiv_id",
    # Utils
    "doi_to_url",
    "latex_to_unicode",
    "remove_accented_characters",
    # Config
    "Configuration",
    # Hooks
    "register_hook",
    "hooks",
    # Base module
    "BaseModule",
]
