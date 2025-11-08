#!/usr/bin/env python
"""
Simple test script for interactive mode functions.
"""

from doi2bibtex.interactive import search_paper_by_title, format_authors, get_clipboard_image
from doi2bibtex.config import Configuration

def test_search():
    """Test search functionality"""
    print("Testing search...")
    results = search_paper_by_title("quantum computing", limit=3)
    print(f"✓ Found {len(results)} results")

    if results:
        print(f"✓ First result: {results[0]['title'][:50]}...")
        print(f"✓ DOI: {results[0]['doi']}")
        print(f"✓ Year: {results[0]['year']}")

        # Test format_authors
        authors_str = format_authors(results[0]['authors'])
        print(f"✓ Authors: {authors_str}")

    print()

def test_clipboard():
    """Test clipboard detection"""
    print("Testing clipboard...")
    img = get_clipboard_image()
    if img is None:
        print("✓ No image in clipboard (expected)")
    else:
        print(f"✓ Image found in clipboard: {type(img)}")
    print()

def test_config():
    """Test config loading"""
    print("Testing config...")
    config = Configuration()
    print(f"✓ Config loaded: {config}")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("Interactive Mode Test Suite")
    print("=" * 50)
    print()

    try:
        test_config()
        test_search()
        test_clipboard()

        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
