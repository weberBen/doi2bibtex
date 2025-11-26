"""
PlainCLI module - provides plain text output for doi2bibtex.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import sys
from argparse import ArgumentParser, Namespace

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.config import Configuration


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class PlaincliModule(BaseModule):
    """
    Module that provides plain text CLI output.

    Adds the --plain flag to output bibtex without formatting.
    """

    def register_hooks(self) -> None:
        """Register hooks for plain CLI output."""
        self._register_hook("cli_exec", self.exec_cli)

    @staticmethod
    def add_cli_args(parser: ArgumentParser) -> None:
        """Add CLI arguments (called before config is loaded)."""
        parser.add_argument(
            "identifier",
            metavar="IDENTIFIER",
            nargs="?",
            help="Identifier to resolve (DOI, arXiv ID, ISBN, or ADS bibcode).",
        )
        parser.add_argument(
            "--plain",
            action="store_true",
            help="Print result as plain text. Useful for piping to other programs.",
        )

    def exec_cli(self, args: Namespace, config: Configuration) -> bool:
        """
        Execute plain CLI output if --plain flag is set.

        Returns:
            True if command was handled, False otherwise
        """
        # Only handle if --plain is set and we have an identifier
        if not getattr(args, "plain", False):
            return False

        identifier = getattr(args, "identifier", None)
        if not identifier:
            print("Error: No identifier provided", file=sys.stderr)
            return True

        # Import here to avoid circular imports
        from doi2bibtex.resolve import resolve_identifier

        # Get the BibTeX entry and print it
        bibtex = resolve_identifier(identifier=identifier, config=config)
        sys.stdout.write(bibtex + "\n")

        return True
