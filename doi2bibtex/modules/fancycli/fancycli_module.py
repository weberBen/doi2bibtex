"""
FancyCLI module - provides rich formatted output for doi2bibtex.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from argparse import Namespace

from rich.console import Console, Text
from rich.syntax import Syntax

from doi2bibtex.modules.base import BaseModule
from doi2bibtex.config import Configuration


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class FancycliModule(BaseModule):
    """
    Module that provides fancy rich console output.

    This is the default output mode when --plain is not specified.
    """

    def register_hooks(self) -> None:
        """Register hooks for fancy CLI output."""
        self._register_hook("cli_exec", self.exec_cli)

    def exec_cli(self, args: Namespace, config: Configuration) -> bool:
        """
        Execute fancy CLI output (default mode).

        This should run after plaincli checks for --plain flag.

        Returns:
            True if command was handled, False otherwise
        """
        # Don't handle if --plain is set (let plaincli handle it)
        if getattr(args, "plain", False):
            return False

        identifier = getattr(args, "identifier", None)
        if not identifier:
            # No identifier provided, show help or error
            return False

        # Import here to avoid circular imports
        from doi2bibtex.resolve import resolve_identifier

        # Set up a rich Console for fancy output
        console = Console()
        text = Text("\nd2b: Resolve DOIs and arXiv IDs to BibTeX\n", style="bold")
        console.print(text)

        # Get the BibTeX entry with a status spinner
        with console.status(f'Resolving identifier "{identifier}" ...'):
            bibtex = resolve_identifier(identifier=identifier, config=config)

        console.print(f'BibTeX entry for identifier "{identifier}":\n')

        # Apply syntax highlighting
        syntax = Syntax(
            code=bibtex,
            lexer="bibtex",
            theme=config.pygments_theme,
            word_wrap=True,
        )

        # Print the result
        console.print(syntax)
        console.print("\n")

        return True
