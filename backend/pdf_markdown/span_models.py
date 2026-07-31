"""
Pure dataclasses for the PDF span model.

Single source of truth for the text layout consumed by formula_extractor,
metadata_rules, merge_engine, and LLM annotation. No logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Span:
    """A single span from PyMuPDF's get_text('dict')."""
    text: str
    char_start: int      # global character offset in document
    char_end: int        # exclusive
    font_name: str
    font_size: float
    is_bold: bool         # flags & 16
    is_italic: bool       # flags & 2
    is_monospace: bool    # flags & 8 or mono font name
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1) in page points
    page_number: int
    separator_after: str = ""  # "\n" (inter-line) or "\n\n" (inter-block/page) or ""


@dataclass
class SpanGroup:
    """A group of consecutive spans sharing the same format state."""
    spans: list[Span]
    is_bold: bool
    is_italic: bool
    is_monospace: bool
    text: str             # concatenated text
    char_start: int       # start of first span
    char_end: int         # end of last span (exclusive, not including separator)
