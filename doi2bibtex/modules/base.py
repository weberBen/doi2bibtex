"""
Base module class for doi2bibtex modules.

All modules (built-in and custom) should inherit from BaseModule.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from doi2bibtex.config import Configuration
from doi2bibtex.hooks import register_hook


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

class BaseModule(ABC):
    """
    Abstract base class for all doi2bibtex modules.

    Modules extend the functionality of doi2bibtex by registering hooks
    that are called at specific points in the execution flow.

    To create a new module:
    1. Create a new directory in doi2bibtex/modules/ or ~/.doi2bibtex/modules/
    2. Create a class that inherits from BaseModule
    3. Implement the register_hooks() method to register your hooks
    4. Add the module name to config.modules

    Example:
        class MyModule(BaseModule):
            def register_hooks(self):
                self._register_hook("identify", self.identify)
                self._register_hook("resolve", self.resolve)

            def identify(self, identifier: str) -> Optional[str]:
                if self._is_my_type(identifier):
                    return "my_type"
                return None

            def resolve(self, identifier_type: str, identifier: str) -> Optional[dict]:
                if identifier_type != "my_type":
                    return None
                return self._fetch_bibtex(identifier)
    """

    def __init__(self, config: Configuration):
        """
        Initialize the module with the given configuration.

        Args:
            config: The application configuration
        """
        self.config = config
        self.register_hooks()

    @abstractmethod
    def register_hooks(self) -> None:
        """
        Register hooks for this module.

        Subclasses must implement this method to register their hooks
        using self._register_hook().

        Available hooks:
        - "cli_arg_parse": Add CLI arguments (static, parser) -> None
        - "cli_exec": Handle CLI execution (args, config) -> bool
        - "identify": Identify identifier type (identifier) -> str|None
        - "resolve": Resolve identifier (type, identifier) -> dict|None
        - "before_postprocess_bibtex": Before postprocessing (type, id, dict, config) -> dict
        - "after_postprocess_bibtex": After postprocessing (type, id, dict, config) -> dict
        """
        pass

    def _register_hook(self, hook_name: str, callback) -> None:
        """
        Register a hook callback.

        Args:
            hook_name: Name of the hook
            callback: Function to call when hook is triggered
        """
        register_hook(hook_name, callback)

    def should_include_abstract(self) -> bool:
        """
        Check if abstracts should be included in bibtex entries.

        Returns:
            True if abstract is not in the remove_fields list
        """
        return "abstract" not in self.config.remove_fields.get("all", [])

    @staticmethod
    def add_cli_args(parser) -> None:
        """
        Static method to add CLI arguments.

        Override this in subclasses that need to add CLI arguments.
        This is called before the config is loaded.

        Args:
            parser: The ArgumentParser instance
        """
        pass
