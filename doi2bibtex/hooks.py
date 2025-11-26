"""
Hook system for doi2bibtex modules.

Hooks allow modules to extend the functionality of doi2bibtex at specific
points in the execution flow.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from typing import Callable, Dict, List


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

# Global hooks registry
hooks: Dict[str, List[Callable]] = {
    # Hook for adding CLI arguments - static method, called before config exists
    # Signature: (parser: ArgumentParser) -> None
    "cli_arg_parse": [],

    # Hook for CLI execution - return True to indicate the command was handled
    # Signature: (args: Namespace, config: Configuration) -> bool
    "cli_exec": [],

    # Hook for identifying identifier type - return type string or None
    # Signature: (identifier: str) -> str | None
    "identify": [],

    # Hook for resolving identifier - return bibtex dict or None
    # Signature: (identifier_type: str, identifier: str) -> dict | None
    "resolve": [],

    # Hook before postprocessing bibtex
    # Signature: (identifier_type: str, identifier: str, bibtex_dict: dict, config: Configuration) -> dict
    "before_postprocess_bibtex": [],

    # Hook after postprocessing bibtex
    # Signature: (identifier_type: str, identifier: str, bibtex_dict: dict, config: Configuration) -> dict
    "after_postprocess_bibtex": [],
}


def register_hook(hook_name: str, callback: Callable) -> None:
    """
    Register a callback function for a specific hook.

    Args:
        hook_name: Name of the hook to register for
        callback: Function to call when the hook is triggered
    """
    if hook_name not in hooks:
        raise ValueError(f"Unknown hook: {hook_name}")
    hooks[hook_name].append(callback)


def clear_hooks() -> None:
    """
    Clear all registered hooks. Useful for testing.
    """
    for hook_name in hooks:
        hooks[hook_name] = []
