#!/usr/bin/env python
"""
Test script for interactive mode with DOI resolution.
"""

from doi2bibtex.config import Configuration
from doi2bibtex.resolve import resolve_identifier

def test_doi_resolution():
    """Test DOI resolution functionality"""
    print("Testing DOI resolution...")

    # Test with a known DOI
    config = Configuration()
    test_doi = "10.1038/nature12373"

    try:
        bibtex = resolve_identifier(identifier=test_doi, config=config)
        print(f"✓ DOI resolution successful")
        print(f"✓ BibTeX entry length: {len(bibtex)} characters")
        print(f"\nSample output (first 200 chars):")
        print(bibtex[:200] + "...")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Mode Switching Test")
    print("=" * 50)
    print()

    success = test_doi_resolution()

    print()
    print("=" * 50)
    if success:
        print("DOI mode test passed! ✓")
    else:
        print("DOI mode test failed! ✗")
    print("=" * 50)
