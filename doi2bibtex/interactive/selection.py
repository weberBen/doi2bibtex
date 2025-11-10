from typing import List, Dict, Optional, Any

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText

from doi2bibtex.interactive.utils import parse_jats_text, format_authors


def key_bindings(current_index=None, show_abstract=None, selected_doi=None, app_ref=None, results=None):
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
    
    return kb

def display_text(current_index=None, show_abstract=None, results=None, original_query=None):
    """Generate the display text based on current state"""
    if show_abstract[0]:
        # Show abstract for current selection
        result = results[current_index[0]]
        raw_abstract = result.get("abstract", "")

        # Parse JATS XML if present and check if abstract exists
        if raw_abstract:
            abstract = parse_jats_text(raw_abstract)
            abstract_style = ""
        else:
            abstract = "No abstract available"
            abstract_style = "red"

        text = FormattedText([
            ("cyan bold", f"\nAbstract for: {result['title']}\n\n"),
            (abstract_style, abstract),
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

def app(
    results: List[Dict[str, Any]],
    original_query: str,
    Console: Any,
    config: Dict,
) -> Optional[str]:
    """
    Display results and let user navigate and select using arrow keys.
    Returns the selected DOI or None if user cancelled.
    """

    current_index = [0]
    show_abstract = [False]
    selected_doi = [None]
    app_ref = [None]

    
    kb  = key_bindings(
      current_index=current_index,
      show_abstract=show_abstract,
      selected_doi=selected_doi,
      app_ref=app_ref,
      results=results
    )

    get_display_text = lambda: display_text(
        current_index=current_index,
        show_abstract=show_abstract,
        results=results,
        original_query=original_query
    )
    
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

    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        return None

    return selected_doi[0]