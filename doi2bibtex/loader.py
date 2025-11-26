"""
Module loader for doi2bibtex.

Handles loading of both built-in modules (from doi2bibtex/modules/)
and custom modules (from ~/.doi2bibtex/modules/).

Loading is done in 2 phases:
1. discover_modules() - Find and import module classes (no instantiation)
2. instantiate_modules() - Create instances with config

This allows CLI argument parsing to happen between phases.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from pathlib import Path
from typing import Dict, List, Any, Optional, Type
import importlib
import importlib.util
import sys

from doi2bibtex.config import Configuration


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

# Path to built-in modules
BUILTIN_MODULES_PATH = Path(__file__).parent / "modules"

# Path to custom modules
CUSTOM_MODULES_PATH = Path.home() / ".doi2bibtex" / "modules"

# Keep track of discovered module classes (phase 1)
discovered_modules: Dict[str, Type] = {}

# Keep track of instantiated modules (phase 2)
loaded_modules: Dict[str, Any] = {}


def get_module_class_name(module_name: str) -> str:
    """
    Convert module name to expected class name.
    Format: <name> -> <Name>Module

    Example: "plaincli" -> "PlaincliModule"
             "arxiv" -> "ArxivModule"
             "my_custom" -> "My_customModule"
    """
    return module_name.capitalize() + "Module"


def get_module_file_name(module_name: str) -> str:
    """
    Get the expected module file name.
    Format: <name>_module.py
    """
    return f"{module_name}_module.py"


def discover_builtin_module(module_name: str) -> Optional[Type]:
    """
    Discover a built-in module class from doi2bibtex/modules/{module_name}/

    Expected structure:
        doi2bibtex/modules/{module_name}/
            __init__.py
            {module_name}_module.py  -> contains {ModuleName}Module class

    Args:
        module_name: Name of the module to discover

    Returns:
        The module class, or None if not found
    """
    module_path = BUILTIN_MODULES_PATH / module_name
    module_file = module_path / get_module_file_name(module_name)

    if not module_file.exists():
        return None

    try:
        # Import the module package
        full_module_name = f"doi2bibtex.modules.{module_name}"
        module = importlib.import_module(full_module_name)

        # Get the module class
        class_name = get_module_class_name(module_name)
        if hasattr(module, class_name):
            return getattr(module, class_name)

        return None
    except ImportError as e:
        print(f"Warning: Failed to load built-in module '{module_name}': {e}")
        return None


def discover_custom_module(module_name: str) -> Optional[Type]:
    """
    Discover a custom module class from ~/.doi2bibtex/modules/{module_name}/

    Expected structure:
        ~/.doi2bibtex/modules/{module_name}/
            __init__.py   # Should export the module class
            {module_name}_module.py  # Contains the module class

    The __init__.py should contain:
        from .{module_name}_module import {ModuleName}Module

    Args:
        module_name: Name of the module to discover

    Returns:
        The module class, or None if not found
    """
    module_path = CUSTOM_MODULES_PATH / module_name
    module_file = module_path / get_module_file_name(module_name)

    if not module_file.exists():
        return None

    init_file = module_path / "__init__.py"
    if not init_file.exists():
        print(f"Warning: Custom module '{module_name}' has no __init__.py")
        return None

    try:
        # Create a unique module name to avoid conflicts
        unique_module_name = f"doi2bibtex_custom_{module_name}"

        # Load the module using importlib.util
        spec = importlib.util.spec_from_file_location(
            unique_module_name,
            init_file,
            submodule_search_locations=[str(module_path)]
        )

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        # Add paths for relative imports
        parent_path = str(CUSTOM_MODULES_PATH)
        if parent_path not in sys.path:
            sys.path.insert(0, parent_path)

        module_path_str = str(module_path)
        if module_path_str not in sys.path:
            sys.path.insert(0, module_path_str)

        # Register and load the module
        sys.modules[unique_module_name] = module
        spec.loader.exec_module(module)

        # Get the module class
        class_name = get_module_class_name(module_name)
        if hasattr(module, class_name):
            return getattr(module, class_name)

        return None

    except Exception as e:
        print(f"Warning: Failed to load custom module '{module_name}': {e}")
        return None


def discover_module(module_name: str) -> Optional[Type]:
    """
    Discover a module class by name. First tries built-in, then custom.

    Args:
        module_name: Name of the module to discover

    Returns:
        The module class, or None if not found
    """
    # Try built-in first
    module_class = discover_builtin_module(module_name)
    if module_class is not None:
        return module_class

    # Try custom
    module_class = discover_custom_module(module_name)
    if module_class is not None:
        return module_class

    print(f"Warning: Module '{module_name}' not found")
    return None


def discover_all_modules(module_names: List[str]) -> Dict[str, Type]:
    """
    Phase 1: Discover all module classes without instantiating them.

    This allows calling static methods (like add_cli_args) before
    the config is loaded.

    Args:
        module_names: List of module names to discover

    Returns:
        Dict mapping module names to their classes
    """
    global discovered_modules
    discovered_modules.clear()

    for module_name in module_names:
        module_class = discover_module(module_name)
        if module_class is not None:
            discovered_modules[module_name] = module_class

    return discovered_modules


def instantiate_all_modules(config: Configuration) -> List[Any]:
    """
    Phase 2: Instantiate all discovered modules with the config.

    Must be called after discover_all_modules().

    Args:
        config: The configuration object

    Returns:
        List of instantiated module objects
    """
    global loaded_modules
    loaded_modules.clear()
    instances = []

    for module_name, module_class in discovered_modules.items():
        try:
            instance = module_class(config)
            loaded_modules[module_name] = instance
            instances.append(instance)
        except Exception as e:
            print(f"Warning: Failed to instantiate module '{module_name}': {e}")

    return instances


def get_discovered_modules() -> Dict[str, Type]:
    """
    Get all discovered module classes.
    """
    return discovered_modules


def get_loaded_module(module_name: str) -> Optional[Any]:
    """
    Get an instantiated module by name.
    """
    return loaded_modules.get(module_name)


def clear_all() -> None:
    """
    Clear all discovered and loaded modules. Useful for testing.
    """
    discovered_modules.clear()
    loaded_modules.clear()
