"""
Provide a command line interface for doi2bibtex.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from argparse import ArgumentParser, Namespace
from typing import Any

import sys

from doi2bibtex import __version__
from doi2bibtex.config import Configuration, DEFAULT_MODULES
from doi2bibtex.hooks import hooks
from doi2bibtex.loader import discover_all_modules, instantiate_all_modules, get_discovered_modules


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def parse_cli_args(args: Any = None) -> Namespace:
    """
    Parse the command line arguments.

    This is called AFTER modules are discovered (but not instantiated),
    so that static add_cli_args methods can add their arguments.
    """
    parser = ArgumentParser(
        prog="d2b",
        description="Resolve DOIs, arXiv IDs, ISBNs, and ADS bibcodes to BibTeX entries.",
    )

    # Call static add_cli_args on all discovered module classes
    for module_class in get_discovered_modules().values():
        if hasattr(module_class, "add_cli_args"):
            module_class.add_cli_args(parser)

    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the version number and exit.",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a custom configuration file.",
    )

    parsed_args = parser.parse_args(args)
    return parsed_args


def main() -> None:  # pragma: no cover
    """
    Main entry point for the CLI.

    Loading order:
    1. Discover module classes (no instantiation)
    2. Parse CLI arguments (using static methods on classes)
    3. Load configuration (possibly from custom path via --config)
    4. Instantiate modules with config (registers hooks)
    5. Execute CLI hooks
    """
    # Phase 1: Discover module classes (no instantiation yet)
    # Use default modules list - config not loaded yet
    discover_all_modules(DEFAULT_MODULES)

    # Phase 2: Parse CLI arguments
    # Static add_cli_args methods are called on discovered classes
    args = parse_cli_args(sys.argv[1:])

    # Print the version number and exit if requested
    if args.version:
        print(__version__)
        sys.exit(0)

    # Phase 3: Load configuration (with optional custom path)
    config = Configuration(config_path=args.config)

    # Phase 4: Instantiate modules with config
    # This registers their hooks
    instantiate_all_modules(config)

    # Phase 5: Execute CLI hooks until one handles the command
    for hook in hooks["cli_exec"]:
        if hook(args, config):
            sys.exit(0)

    # If no hook handled the command, show help
    print("Error: No identifier provided. Use -h for help.", file=sys.stderr)
    sys.exit(1)
