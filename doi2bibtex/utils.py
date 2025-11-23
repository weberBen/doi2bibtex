"""
Utility functions.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from pylatexenc.latex2text import LatexNodes2Text
from unidecode import unidecode

import re
import html
import urllib.parse
import bs4


# -----------------------------------------------------------------------------
# DEFINITIONS
# -----------------------------------------------------------------------------

def doi_to_url(doi: str) -> str:
    """
    Convert a DOI to a URL.
    """

    encoded_doi = urllib.parse.quote(doi, safe="")
    return f"https://doi.org/{encoded_doi}"


def latex_to_unicode(text: str) -> str:
    """
    Convert LaTeX-escaped to Unicode. Example: "{\"a}" -> "ä".
    Note: characters in math mode are *not* converted.
    """
    return str(LatexNodes2Text(math_mode='verbatim').latex_to_text(text))


def remove_accented_characters(string: str) -> str:
    """
    Remove accented characters from a string (e.g., to generate an
    ASCII-compatible citekey).
    """

    # Manually replace some characters
    string = string.replace("Ä", "Ae")
    string = string.replace("Ö", "Oe")
    string = string.replace("Ü", "Ue")
    string = string.replace("ä", "ae")
    string = string.replace("ö", "oe")
    string = string.replace("ü", "ue")
    string = string.replace("ß", "ss")

    # Use unidecode to replace the rest (e.g., "é" -> "e")
    string = str(unidecode(string, "utf-8"))

    return string

def unescape_jats_text(text: str) -> str:
    """
    Parse JATS  (Journal Article Tag Suite) XML text (without adding external library) and convert to clean text.
    """
    if not text:
        return text
    
    # Check if it contains JATS XML tags
    if '<jats:' not in text and '<' not in text:
        return text

    try:
        # Parse with BeautifulSoup (use html.parser for better namespace handling)
        soup = bs4.BeautifulSoup(text, 'html.parser')

        # Remove <jats:title> tags (usually "Abstract")
        for title in soup.find_all(['jats:title', 'title']):
            title.decompose()

        # Get text from all paragraph tags
        paragraphs = soup.find_all(['jats:p', 'p'])
        if paragraphs:
            # Extract text from each paragraph and join with double newline
            text_parts = []
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if text:
                    text_parts.append(text)
            text = '\n\n'.join(text_parts)
        else:
            # No paragraph tags, get all text
            text = soup.get_text(separator=' ', strip=True)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s+\n', '\n\n', text)

        return text.strip()

    except Exception:
        # If parsing fails, try simple regex cleanup
        text = re.sub(r'<jats:[^>]+>', '', text)
        text = re.sub(r'</?[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

def unescape_ampersand(text: str) -> str:
    """
    Fix broken ampersand
    """
    text = text.replace(
        r"{\&}amp$\mathsemicolon$", r"\&"
    )
    text = text.replace(
        r"&amp;", r"\&"
    )

    return text

def unescape_text(text: str) -> str:
    """
    Clean text by decoding HTML entities and converting LaTeX to Unicode.

    APIs may return text with:
    - HTML entities (e.g., &amp; -> &, &lt; -> <)
    - LaTeX commands (e.g., {\bf text} -> text, $\approx$ -> ≈)

    This function handles both conversions for cleaner display.
    """
    if not text:
        return text

    try:
        # First decode HTML entities
        text = html.unescape(text)
    except:
        pass

    # Pre-process problematic LaTeX commands that pylatexenc can't handle
    # Remove \href{url}{text} -> text
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)
    # Remove lone URLs in \href
    text = re.sub(r'\\href\{([^}]*)\}', r'\1', text)

    # Then convert LaTeX to Unicode text
    try:
        latex_converter = LatexNodes2Text(
            keep_braced_groups=False,
            strict_latex_spaces=False
        )
        text = latex_converter.latex_to_text(text)
    except Exception:
        pass

    try:
        text = unescape_jats_text(text)
    except:
        pass

    try:
        text = unescape_ampersand(text)
    except:
        pass

    return text

