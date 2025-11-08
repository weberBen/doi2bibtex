#!/usr/bin/env python
"""
Test script to verify history behavior.
This script simulates the history navigation logic.
"""

def test_history_navigation():
    """Test that history entries are saved when navigating"""

    print("Testing history navigation with modifications...")
    print()

    # Simulate the history system
    input_history = ["titre 1", "titre 2"]
    history_index = [None]
    current_draft = [None]
    current_text = ""

    print(f"Initial history: {input_history}")
    print()

    # Simulate: User is at fresh prompt with "titre 3" (not validated)
    current_text = "titre 3"
    print(f"Current text (not validated): '{current_text}'")

    # User presses UP (go to history)
    print("User presses UP arrow...")
    if history_index[0] is None:
        current_draft[0] = current_text
        history_index[0] = len(input_history) - 1
    current_text = str(input_history[history_index[0]])
    print(f"  → Now at history[{history_index[0]}]: '{current_text}'")
    print(f"  → Draft saved: '{current_draft[0]}'")
    print()

    # User presses UP again
    print("User presses UP arrow again...")
    if history_index[0] > 0:
        # Save current modifications to history before moving
        input_history[history_index[0]] = current_text
        history_index[0] -= 1
        # DON'T reset draft - it should remain intact
    current_text = str(input_history[history_index[0]])
    print(f"  → Now at history[{history_index[0]}]: '{current_text}'")
    print(f"  → History: {input_history}")
    print(f"  → Draft still: '{current_draft[0]}'")
    print()

    # User modifies the text
    print("User modifies 'titre 1' to 'titre 1 modifié'...")
    current_text = "titre 1 modifié"
    print(f"  → Current text: '{current_text}'")
    print()

    # User presses DOWN
    print("User presses DOWN arrow...")
    # Save current modifications to history before moving
    input_history[history_index[0]] = current_text
    if history_index[0] < len(input_history) - 1:
        history_index[0] += 1
        # DON'T reset draft - it should remain intact
        current_text = str(input_history[history_index[0]])
    print(f"  → Now at history[{history_index[0]}]: '{current_text}'")
    print(f"  → History updated: {input_history}")
    print(f"  → Draft still: '{current_draft[0]}'")
    print()

    # User presses DOWN again to go back to draft
    print("User presses DOWN arrow to return to draft...")
    # Save current modifications to history before moving
    input_history[history_index[0]] = current_text
    if history_index[0] < len(input_history) - 1:
        history_index[0] += 1
        current_text = str(input_history[history_index[0]])
    else:
        # Restore draft when going past the end
        history_index[0] = None
        current_text = current_draft[0] if current_draft[0] is not None else ""
    print(f"  → Returned to draft: '{current_text}'")
    print(f"  → History: {input_history}")
    print()

    # Verify
    expected = "titre 3"
    if current_text == expected:
        print(f"✓ SUCCESS: Got draft '{current_text}' as expected!")
        return True
    else:
        print(f"✗ FAIL: Expected draft '{expected}' but got '{current_text}'")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("History Navigation Test")
    print("=" * 60)
    print()

    success = test_history_navigation()

    print()
    print("=" * 60)
    if success:
        print("Test PASSED ✓")
    else:
        print("Test FAILED ✗")
    print("=" * 60)
