"""
Interactive console mode for searching papers by title.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from typing import List, Dict, Optional, Any


from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText

from doi2bibtex.resolve import resolve_identifier, resolve_title

# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

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
                except ImportError:
                    console.print("\n[yellow]Note: Install 'pyperclip' for clipboard copy functionality[/yellow]\n")
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
                except ImportError:
                    console.print("\n[yellow]Note: Install 'pyperclip' for clipboard copy functionality[/yellow]\n")
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
                except ImportError:
                    console.print("[yellow]Note: Install 'pyperclip' for clipboard copy functionality[/yellow]\n")
                except Exception as e:
                    console.print(f"[yellow]Could not copy to clipboard: {e}[/yellow]\n")
            else:
                console.print()
    except (KeyboardInterrupt, EOFError):
        console.print()

    console.print()  # Add spacing before returning to interactive mode

def format_authors(authors: List[Dict[str, str]], max_authors: int = 3) -> str:
    """
    Format author list for display, showing only first N authors.
    """
    if not authors:
        return "Unknown authors"

    formatted = []
    for author in authors[:max_authors]:
        given = author.get("given", "")
        family = author.get("family", "")
        if given and family:
            formatted.append(f"{given} {family}")
        elif family:
            formatted.append(family)

    if len(authors) > max_authors:
        formatted.append("et al.")

    return ", ".join(formatted)


def get_clipboard_image():
    """
    Get image from clipboard if available.
    Returns PIL Image or None.
    """
    from PIL import ImageGrab
    
    try:
        # Try to get image from clipboard
        img = ImageGrab.grabclipboard()
        if img is not None and hasattr(img, 'save'):
            return img

        return None
    except Exception:
        return None


def normalize_text(text):
    import re

    # remove control char
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    # remove extra space line break, tabulation, ect
    text = re.sub(r'\s+', ' ', text)

    return text

def ocr_image(image_source, console: Console) -> str:
    """
    Perform OCR on an image to extract text using RapidOCR.
    image_source can be a file path (str) or PIL Image object.
    """

    # lazy import to avoid console launch delay
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR


    try:
        # Display OCR in progress animation
        with console.status("[cyan]OCR in progress...", spinner="dots"):
            # Initialize RapidOCR engine
            engine = RapidOCR()

            # Convert image to numpy array if needed
            if isinstance(image_source, str):
                # RapidOCR can handle file paths directly
                img_input = image_source
            else:
                # Convert PIL Image to numpy array
                img_input = np.array(image_source)

            # Perform OCR
            result, elapse = engine(img_input)

            # Extract text from results
            # result is a list of [bbox, text, score] or None if no text detected
            if result is None or len(result) == 0:
                return ""

            text_lines = [detection[1] for detection in result]
            text = '\n'.join(text_lines)

            return normalize_text(text)

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

    # History for navigating previous inputs
    input_history = []
    history_index = [None]  # None means we're not in history mode
    current_draft = [None]  # Save current text when navigating history
    search_mode = ["title"]  # "title" or "doi"
    toolbar_message = [None]  # Message to display in toolbar (persistent across iterations)

    while True:
        # Determine prompt based on search mode
        prompt_text = "Title: " if search_mode[0] == "title" else "DOI: "

        # Create text area for input
        text_area = TextArea(
            multiline=True,  # Need True for wrap_lines to work visually
            wrap_lines=True,  # Wrap long text visually on multiple lines
            prompt=prompt_text,
            accept_handler=None  # We'll handle Enter manually
        )

        # Key bindings
        kb = KeyBindings()
        search_triggered = {"value": False}
        ocr_mode = {"active": False}
        mode_switched = {"value": False}

        @kb.add('enter')
        def _(event):
            """Launch search on Enter"""
            toolbar_message[0] = None  # Clear any message
            search_triggered["value"] = True
            current_draft[0] = None  # Reset draft when validating
            event.app.exit()

        @kb.add('c-v')  # Ctrl+V for image paste only
        def _(event):
            """Paste image from clipboard for OCR"""
            # Try to get image from clipboard
            clipboard_image = get_clipboard_image()

            if clipboard_image:
                # It's an image! Trigger OCR mode
                ocr_mode["active"] = True
                event.app.exit()
            else:
                # No image in clipboard - show message in toolbar
                toolbar_message[0] = ("warning", "No image in clipboard. Use Ctrl+Shift+V to paste text.")

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
                doc = text_area.buffer.document
                return doc.cursor_position_row == 0 or len(doc.text) == 0
            except:
                return True

        @Condition
        def on_last_line_or_empty():
            """True if cursor on last line or text is empty"""
            try:
                doc = text_area.buffer.document
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
            # Mark mode switch to avoid triggering search
            mode_switched["value"] = True
            event.app.exit()

        @kb.add('c-c')
        def _(event):
            """Exit on Ctrl+C"""
            event.app.exit()

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

        # Create toolbar window
        toolbar_window = Window(
            content=FormattedTextControl(get_bottom_toolbar),
            height=1,
            style='bg:#2e3440'  # Dark background for toolbar
        )

        # Create application with EMACS editing mode
        app = Application(
            layout=Layout(HSplit([text_area, toolbar_window])),
            key_bindings=kb,
            full_screen=False,
            mouse_support=True,
            editing_mode=EditingMode.EMACS,  # Use EMACS mode for modern controls
            enable_page_navigation_bindings=False,  # Disable default page nav to avoid conflicts
        )

        # Run the application
        try:
            app.run()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting interactive mode.[/yellow]")
            return

        # Check if OCR mode was triggered
        if ocr_mode["active"]:
            clipboard_image = get_clipboard_image()
            if clipboard_image:
                console.print("\n[green]Image detected![/green]")

                # Perform OCR on the clipboard image
                ocr_text = ocr_image(clipboard_image, console)

                if ocr_text.startswith("Error:"):
                    console.print(f"[red]{ocr_text}[/red]")
                    continue

                console.print(f"\n[green]Extracted text:[/green]\n{ocr_text}\n")
                console.print("[cyan]Edit the text if needed, then press Enter to search[/cyan]\n")

                # Create new text area with OCR text
                text_area_ocr = TextArea(
                    multiline=True,
                    wrap_lines=True,
                    prompt="Edit: ",
                    text=ocr_text
                )

                # Create new application for editing OCR text (reuse same bindings)
                ocr_app = Application(
                    layout=Layout(HSplit([text_area_ocr])),
                    key_bindings=kb,
                    full_screen=False,
                    mouse_support=True,
                    editing_mode=EditingMode.EMACS,
                )

                # Update text_area reference for later use
                text_area = text_area_ocr

                try:
                    ocr_app.run()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[yellow]Search cancelled.[/yellow]")
                    continue

        # If mode was switched, restart loop to show new prompt
        if mode_switched["value"]:
            continue

        if not search_triggered["value"]:
            console.print("\n[yellow]Exiting interactive mode.[/yellow]")
            return

        input_text = normalize_text(text_area.text)

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
                toolbar_message = [("error", f"Error resolving identifier: {str(e)[:80]}")]
                continue

        else:
            # Title mode - search for papers
            console.print(f"\n[cyan]Searching for: {input_text}[/cyan]\n")

            try:
                with console.status("Searching..."):
                    results = resolve_title(input_text)

                if not results:
                    # Show message in toolbar on next loop iteration
                    toolbar_message = [("warning", "No results found. Try a different search term.")]
                    continue
            except Exception as e:
                # Show error in toolbar on next loop iteration
                toolbar_message = [("error", f"Search error: {str(e)[:80]}")]
                continue

            # Display results and let user select
            selected_doi = select_from_results(results, input_text, console, config)

            if selected_doi:
                # Get the BibTeX entry for the selected DOI
                console.print(f"\n[cyan]Fetching BibTeX for DOI: {selected_doi}[/cyan]\n")

                with console.status("Fetching BibTeX..."):
                    bibtex = resolve_identifier(identifier=selected_doi, config=config)

                display_bibtex_with_pause(bibtex, console, config)


def select_from_results(
    results: List[Dict[str, Any]],
    original_query: str,
    console,
    config
) -> Optional[str]:
    """
    Display results and let user navigate and select using arrow keys.
    Returns the selected DOI or None if user cancelled.
    """

    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.formatted_text import FormattedText

    current_index = [0]
    show_abstract = [False]
    selected_doi = [None]
    app_ref = [None]

    def get_display_text():
        """Generate the display text based on current state"""
        if show_abstract[0]:
            # Show abstract for current selection
            result = results[current_index[0]]
            abstract = result.get("abstract", "No abstract available")

            text = FormattedText([
                ("cyan bold", f"\nAbstract for: {result['title']}\n\n"),
                ("", abstract),
                ("\n\ncyan", "\nPress [ESC] to return to results\n")
            ])
            return text
        else:
            # Show list of results
            lines = [("cyan bold", f"\nSearch results for: {original_query}\n\n")]

            for i, result in enumerate(results):
                prefix = "> " if i == current_index[0] else "  "
                style = "reverse" if i == current_index[0] else ""

                title = result.get("title", "No title")
                year = result.get("year", "N/A")
                journal = result.get("journal", "N/A")
                authors = format_authors(result.get("authors", []), max_authors=3)

                lines.append((style, f"{prefix}[{i+1}] {title}\n"))
                lines.append((style, f"     Authors: {authors}\n"))
                lines.append((style, f"     Year: {year}, Journal: {journal}\n\n"))

            lines.append(("cyan", "\nNavigation: "))
            lines.append(("", "[↑↓] Select  [SPACE] Abstract  [ENTER] Choose  [ESC] Cancel\n"))

            return FormattedText(lines)

    # Key bindings
    kb = KeyBindings()

    @kb.add('up')
    def _(event):
        """Move selection up"""
        if not show_abstract[0]:
            current_index[0] = max(0, current_index[0] - 1)
            if app_ref[0]:
                app_ref[0].invalidate()

    @kb.add('down')
    def _(event):
        """Move selection down"""
        if not show_abstract[0]:
            current_index[0] = min(len(results) - 1, current_index[0] + 1)
            if app_ref[0]:
                app_ref[0].invalidate()

    @kb.add('space')
    def _(event):
        """Toggle abstract view"""
        if not show_abstract[0]:
            show_abstract[0] = True
            if app_ref[0]:
                app_ref[0].invalidate()

    @kb.add('escape')
    def _(event):
        """Go back or cancel"""
        if show_abstract[0]:
            show_abstract[0] = False
            if app_ref[0]:
                app_ref[0].invalidate()
        else:
            event.app.exit()

    @kb.add('enter')
    def _(event):
        """Select current result"""
        if not show_abstract[0]:
            selected_doi[0] = results[current_index[0]].get("doi")
            event.app.exit()

    @kb.add('c-c')
    @kb.add('c-d')
    def _(event):
        """Exit"""
        event.app.exit()

    # Create the application
    app = Application(
        layout=Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(
                        text=get_display_text,
                        focusable=True
                    ),
                    wrap_lines=True
                )
            ])
        ),
        key_bindings=kb,
        full_screen=False,
        mouse_support=True
    )

    app_ref[0] = app

    # Run the application
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        return None

    return selected_doi[0]