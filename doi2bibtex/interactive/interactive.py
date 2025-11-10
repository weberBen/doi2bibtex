"""
Interactive console mode for searching papers by title.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------


from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.application import get_app

from doi2bibtex.resolve import resolve_identifier, resolve_title

from doi2bibtex.interactive.utils import (
  get_clipboard_image,
  ocr,
  normalize_text,
)

from doi2bibtex.interactive.selection import app as select_from_results

# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

# Special return values for PromptSession control flow
RESULT_MODE_SWITCH = "__MODE_SWITCH__"
RESULT_OCR_REQUESTED = "__OCR_REQUESTED__"


def display_bibtex_with_pause(bibtex: str, console: Console, config) -> None:
    """
    Display BibTeX with syntax highlighting and pause to allow text selection.
    User can optionally copy to clipboard by pressing 'c'.
    """
    console.print(f'[green]BibTeX entry:[/green]\n')

    # Apply syntax highlighting
    syntax = Syntax(
        code=bibtex,
        lexer="bibtex",
        theme=config.pygments_theme,
        word_wrap=True,
    )

    console.print(syntax)
    console.print()

    # Display pause message with copy option
    console.print(Panel.fit(
        "[bold cyan]You can now select and copy the BibTeX text above[/bold cyan]\n\n"
        "[dim]Press 'c' to copy to clipboard + continue, or any other key to continue...[/dim]",
        border_style="cyan"
    ))

    # Read single character without waiting for ENTER
    # This allows text selection since prompt_toolkit is not active
    try:
        import sys
        import tty
        import termios

        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # Set terminal to raw mode to read single character
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1).lower()

            # Restore terminal settings immediately
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

            # If user pressed 'c', copy to clipboard
            if char == 'c':
                try:
                    import pyperclip
                    pyperclip.copy(bibtex)
                    console.print("\n[green bold]✓ BibTeX copied to clipboard![/green bold]\n")
                except Exception as e:
                    console.print(f"\n[yellow]Could not copy to clipboard: {e}[/yellow]\n")
            else:
                console.print()  # Just add newline

        except Exception:
            # Restore settings on error
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            console.print()

    except (ImportError, AttributeError):
        # Fallback for Windows or if termios not available
        try:
            import msvcrt
            char = msvcrt.getch().decode('utf-8').lower()

            if char == 'c':
                try:
                    import pyperclip
                    pyperclip.copy(bibtex)
                    console.print("\n[green bold]✓ BibTeX copied to clipboard![/green bold]\n")
                except Exception as e:
                    console.print(f"\n[yellow]Could not copy to clipboard: {e}[/yellow]\n")
            else:
                console.print()
        except ImportError:
            # Ultimate fallback: use input()
            user_input = input().strip().lower()
            if user_input == 'c':
                try:
                    import pyperclip
                    pyperclip.copy(bibtex)
                    console.print("[green bold]✓ BibTeX copied to clipboard![/green bold]\n")
                except Exception as e:
                    console.print(f"[yellow]Could not copy to clipboard: {e}[/yellow]\n")
            else:
                console.print()
    except (KeyboardInterrupt, EOFError):
        console.print()

    console.print()  # Add spacing before returning to interactive mode

def ocr_image(image_source, console: Console) -> str:
    """
    Perform OCR on an image to extract text using RapidOCR.
    image_source can be a file path (str) or PIL Image object.
    """
    try:
        # Display OCR in progress animation
        with console.status("[cyan]OCR in progress...", spinner="dots"):
            return ocr(image_source)
    except Exception as e:
        return f"Error performing OCR: {e}"


def interactive_mode(config) -> None:
    """
    Interactive console mode for searching papers by title.
    """

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]Interactive Mode[/bold cyan]\n\n"
        "Type or paste a paper title or DOI\n"
        "Paste an image (Ctrl+V) for OCR\n\n"
        "Controls:\n"
        "  [bold]Enter[/bold] - Launch search\n"
        "  [bold]Shift+Tab[/bold] - Switch Title/DOI mode\n"
        "  [bold]Arrows[/bold] - Navigate text\n"
        "  [bold]↑/↓[/bold] - History (on first/last line)\n"
        "  [bold]Ctrl+A/E[/bold] - Start/End of line\n"
        "  [bold]Ctrl+W[/bold] - Delete word backward\n"
        "  [bold]Ctrl+Z[/bold] - Undo\n"
        "  [bold]Ctrl+V[/bold] - Paste image for OCR\n"
        "  [bold]Ctrl+Shift+V[/bold] - Paste text (terminal native)\n"
        "  [bold]Ctrl+C[/bold] - Exit",
        border_style="cyan"
    ))

    # State variables
    input_history = []
    history_index = [None]  # None means we're not in history mode
    current_draft = [None]  # Save current text when navigating history
    search_mode = ["title"]  # "title" or "doi"
    toolbar_message = [None]  # Message to display in toolbar (persistent across iterations)

    # Key bindings - defined once, reused for all prompts
    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        """Validate input on Enter (overrides default multiline behavior)"""
        event.app.exit(result=event.current_buffer.text)

    @kb.add('c-v')  # Ctrl+V for image paste only
    def _(event):
        """Paste image from clipboard for OCR"""
        # Try to get image from clipboard
        clipboard_image = get_clipboard_image()

        if clipboard_image:
            # It's an image! Exit with special result to trigger OCR mode
            event.app.exit(result=RESULT_OCR_REQUESTED)
        else:
            # No image in clipboard - show message in toolbar
            toolbar_message[0] = ("warning", "No image")

    @kb.add('c-^')  # Ctrl+6 (Ctrl+^ on US keyboards)
    @kb.add('c-a', 'c-a')  # Alternative: Ctrl+A twice
    def _(event):
        """Select all text"""
        buffer = event.current_buffer
        buffer.cursor_position = 0
        buffer.start_selection()
        buffer.cursor_position = len(buffer.text)

    @kb.add('c-z')  # Ctrl+Z for undo
    def _(event):
        """Undo last edit"""
        event.current_buffer.undo()

    # Conditions for smart arrow history navigation
    @Condition
    def on_first_line_or_empty():
        """True if cursor on first line or text is empty"""
        try:
            app = get_app()
            doc = app.current_buffer.document
            return doc.cursor_position_row == 0 or len(doc.text) == 0
        except:
            return True

    @Condition
    def on_last_line_or_empty():
        """True if cursor on last line or text is empty"""
        try:
            app = get_app()
            doc = app.current_buffer.document
            return doc.cursor_position_row >= doc.line_count - 1 or len(doc.text) == 0
        except:
            return True

    @kb.add('up', filter=on_first_line_or_empty)
    def _(event):
        """Navigate history - previous (only when on first line)"""
        if not input_history:
            return

        # If we're not in history mode, save current text and start from the end
        if history_index[0] is None:
            current_draft[0] = event.current_buffer.text
            history_index[0] = len(input_history) - 1
        elif history_index[0] > 0:
            # Save current modifications to history before moving
            input_history[history_index[0]] = event.current_buffer.text
            history_index[0] -= 1

        # Load history entry (copy to avoid modification of original)
        if 0 <= history_index[0] < len(input_history):
            event.current_buffer.text = str(input_history[history_index[0]])
            event.current_buffer.cursor_position = len(event.current_buffer.text)

    @kb.add('down', filter=on_last_line_or_empty)
    def _(event):
        """Navigate history - next (only when on last line)"""
        if not input_history or history_index[0] is None:
            return

        # Save current modifications to history before moving
        input_history[history_index[0]] = event.current_buffer.text

        if history_index[0] < len(input_history) - 1:
            history_index[0] += 1
            event.current_buffer.text = str(input_history[history_index[0]])
        else:
            # Restore draft when going past the end
            history_index[0] = None
            event.current_buffer.text = current_draft[0] if current_draft[0] is not None else ""

        event.current_buffer.cursor_position = len(event.current_buffer.text)

    @kb.add('c-p')  # Ctrl+P for previous history (alternative)
    def _(event):
        """Navigate history - previous"""
        if not input_history:
            return

        # If we're not in history mode, save current text and start from the end
        if history_index[0] is None:
            current_draft[0] = event.current_buffer.text
            history_index[0] = len(input_history) - 1
        elif history_index[0] > 0:
            # Save current modifications to history before moving
            input_history[history_index[0]] = event.current_buffer.text
            history_index[0] -= 1

        # Load history entry (copy to avoid modification)
        if 0 <= history_index[0] < len(input_history):
            event.current_buffer.text = str(input_history[history_index[0]])
            event.current_buffer.cursor_position = len(event.current_buffer.text)

    @kb.add('c-n')  # Ctrl+N for next history
    def _(event):
        """Navigate history - next"""
        if not input_history or history_index[0] is None:
            return

        # Save current modifications to history before moving
        input_history[history_index[0]] = event.current_buffer.text

        if history_index[0] < len(input_history) - 1:
            history_index[0] += 1
            event.current_buffer.text = str(input_history[history_index[0]])
        else:
            # Restore draft when going past the end
            history_index[0] = None
            event.current_buffer.text = current_draft[0] if current_draft[0] is not None else ""

        event.current_buffer.cursor_position = len(event.current_buffer.text)

    @kb.add('s-tab')  # Shift+Tab to switch search mode
    def _(event):
        """Switch between title and DOI search modes"""
        # Cycle through modes
        if search_mode[0] == "title":
            search_mode[0] = "doi"
        else:
            search_mode[0] = "title"
        # Exit with special result to switch mode
        event.app.exit(result=RESULT_MODE_SWITCH)

    # Create bottom toolbar showing current mode
    def get_bottom_toolbar():
        """Generate bottom toolbar with mode indicator"""
        # Build mode indicator
        if search_mode[0] == "title":
            toolbar_parts = [
                ('bg:#0066cc #ffffff bold', ' Title Mode '),
                ('', ' | '),
                ('#888888', 'DOI Mode'),
                ('', '     '),
                ('#888888 italic', '(Shift+Tab to cycle)'),
            ]
        else:
            toolbar_parts = [
                ('#888888', 'Title Mode'),
                ('', ' | '),
                ('bg:#0066cc #ffffff bold', ' DOI Mode '),
                ('', '     '),
                ('#888888 italic', '(Shift+Tab to cycle)'),
            ]

        # Add message if present
        if toolbar_message[0] is not None:
            msg_type, msg_text = toolbar_message[0]
            toolbar_parts.append(('', '     '))  # Spacing
            if msg_type == "error":
                toolbar_parts.append(('bg:#d32f2f #ffffff bold', f' ✗ {msg_text} '))
            elif msg_type == "warning":
                toolbar_parts.append(('bg:#f57c00 #ffffff bold', f' ⚠ {msg_text} '))
            elif msg_type == "success":
                toolbar_parts.append(('bg:#388e3c #ffffff bold', f' ✓ {msg_text} '))
            else:  # info
                toolbar_parts.append(('bg:#1976d2 #ffffff', f' ℹ {msg_text} '))

        return FormattedText(toolbar_parts)

    # Create PromptSession - reused for all inputs
    session = PromptSession(
        multiline=True,
        wrap_lines=True,
        editing_mode=EditingMode.EMACS,
        key_bindings=kb,
        bottom_toolbar=get_bottom_toolbar,
        enable_history_search=False,  # We use custom history
    )

    while True:
        # Determine prompt based on search mode
        prompt_text = "Title: " if search_mode[0] == "title" else "DOI: "

        # Clear toolbar message before new prompt
        toolbar_message[0] = None

        # Get input from user using PromptSession
        try:
            result = session.prompt(message=prompt_text)

            # Check for special return values
            if result == RESULT_MODE_SWITCH:
                # User pressed Shift+Tab to switch mode
                continue
            elif result == RESULT_OCR_REQUESTED:
                # User pressed Ctrl+V with an image in clipboard
                clipboard_image = get_clipboard_image()
                if clipboard_image:
                    console.print("\n[green]Image detected![/green]")

                    # Perform OCR on the clipboard image
                    ocr_text = ocr_image(clipboard_image, console)

                    if ocr_text.startswith("Error"):
                        console.print(f"[red]{ocr_text}[/red]")
                        continue

                    console.print(f"\n[green]Extracted text:[/green]\n{ocr_text}\n")
                    console.print("[cyan]Edit the text if needed, then press Enter to search[/cyan]\n")

                    # Get edited OCR text using prompt with default value
                    try:
                        ocr_result = session.prompt(message="Edit: ", default=ocr_text)

                        # Handle special results from OCR editing
                        if ocr_result == RESULT_MODE_SWITCH:
                            continue
                        elif ocr_result == RESULT_OCR_REQUESTED:
                            # Ignore nested OCR requests
                            continue

                        input_text = normalize_text(ocr_result)
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Search cancelled.[/yellow]")
                        continue
                else:
                    # This shouldn't happen (already checked in key binding), but handle it
                    continue
            else:
                # Normal text input
                input_text = normalize_text(result)

            # Reset history navigation state
            current_draft[0] = None
            history_index[0] = None

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting interactive mode.[/yellow]")
            return

        if not input_text:
            console.print("[yellow]No input provided.[/yellow]")
            continue

        # Add to history (avoid duplicates of the last entry)
        if not input_history or input_history[-1] != input_text:
            input_history.append(input_text)
        # Reset history index
        history_index[0] = None

        # Handle based on search mode
        if search_mode[0] == "doi":
            # DOI mode - resolve identifier directly
            console.print(f"\n[cyan]Resolving DOI: {input_text}[/cyan]\n")

            try:
                with console.status("Resolving..."):
                    bibtex = resolve_identifier(identifier=input_text, config=config)

                display_bibtex_with_pause(bibtex, console, config)

            except Exception as e:
                # Show error in toolbar on next loop iteration
                toolbar_message[0] = ("error", f"Error resolving identifier: {str(e)[:80]}")
                continue

        else:
            # Title mode - search for papers
            console.print(f"\n[cyan]Searching for: {input_text}[/cyan]\n")

            try:
                with console.status("Searching..."):
                    results = resolve_title(input_text)

                if not results:
                    # Show message in toolbar on next loop iteration
                    toolbar_message[0] = ("warning", "No results found. Try a different search term.")
                    continue
            except Exception as e:
                # Show error in toolbar on next loop iteration
                toolbar_message[0] = ("error", f"Search error: {str(e)[:80]}")
                continue

            # Display results and let user select
            selected_doi = select_from_results(results, input_text, console, config)

            if selected_doi:
                # Get the BibTeX entry for the selected DOI
                console.print(f"\n[cyan]Fetching BibTeX for DOI: {selected_doi}[/cyan]\n")

                with console.status("Fetching BibTeX..."):
                    bibtex = resolve_identifier(identifier=selected_doi, config=config)

                display_bibtex_with_pause(bibtex, console, config)
