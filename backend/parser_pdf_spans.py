"""
Span-level formatting helpers for PyMuPDF dict text reconstruction.
"""
import re


def _is_mono_font(font_name: str) -> bool:
    """Check if font name suggests a monospace/typewriter face."""
    mono_keywords = ("courier", "mono", "consolas", "code", "source code",
                     "typewriter", "menlo", "dejavu sans mono", "liberation mono",
                     "fira code", "jetbrains", "cascadia", "inconsolata")
    return any(kw in font_name.lower() for kw in mono_keywords)


def _is_bullet_start(line: str) -> bool:
    """Check if a line starts with a bullet or numbered-list marker."""
    stripped = line.strip()
    # Common bullet characters
    if stripped[:1] in "•▪▸▹◦○■□▪" and (len(stripped) < 2 or stripped[1] in (" ", "\t")):
        return True
    # Dash bullet: "- " or "– " at start
    if stripped.startswith(("- ", "– ", "— ")):
        return True
    # Asterisk bullet: "* " (but not "**" which is bold)
    if stripped.startswith("* ") and not stripped.startswith("**"):
        return True
    # Numbered list: "1.", "1)", "(1)", "1 ", "1.1", "i.", "a)"
    import re
    if re.match(r'^[\d]+[.)]\s', stripped):
        return True
    if re.match(r'^\([\d]+\)\s', stripped):
        return True
    if re.match(r'^[ivxlcdm]+[.)]\s', stripped, re.IGNORECASE):
        return True
    if re.match(r'^[a-z][.)]\s', stripped):
        return True
    return False


def _format_spans(spans: list[dict]) -> list[str]:
    """Convert a list of PyMuPDF span dicts to Markdown inline text.

    Each span dict must have 'text', 'flags', 'font' (optional), 'size'.
    Consecutive spans with identical bold/italic/monospace state are merged
    before wrapping, so ``**word1** **word2**`` becomes ``**word1 word2**``.
    """
    # Group consecutive spans that share the same formatting state
    groups: list[tuple[tuple[bool, bool, bool], str]] = []
    cur_state: tuple[bool, bool, bool] | None = None
    cur_text: str = ""

    for sp in spans:
        text = sp.get("text", "")
        if not text:
            continue

        flags = sp.get("flags", 0)
        font = sp.get("font", "")
        is_bold = bool(flags & 16)
        is_italic = bool(flags & 2)
        is_mono = bool(flags & 8) or _is_mono_font(font)
        state = (is_bold, is_italic, is_mono)

        if state == cur_state:
            cur_text += text
        else:
            if cur_text:
                groups.append((cur_state, cur_text))  # type: ignore[arg-type]
            cur_state = state
            cur_text = text

    if cur_text:
        groups.append((cur_state, cur_text))  # type: ignore[arg-type]

    # Wrap each group
    parts: list[str] = []
    for (is_bold, is_italic, is_mono), text in groups:
        text = text.rstrip()
        if not text:
            continue

        if is_bold and is_italic:
            text = f"***{text}***"
        elif is_bold:
            text = f"**{text}**"
        elif is_italic:
            text = f"*{text}*"

        if is_mono:
            text = f"`{text}`"

        parts.append(text)
    return parts


def extract_spans_from_pdf(file_path: str) -> list:
    """Extract spans with character positions and font metadata from a PDF.

    Thin wrapper around pdf_markdown.span_extractor.extract_spans.
    Returns list of Span objects with text, char_start, char_end, font info,
    bbox coordinates, and page_number.
    """
    from pdf_markdown.span_extractor import extract_spans
    return extract_spans(file_path)
