"""
Segment dataclass for sentence-level LLM annotation units.

Each segment carries surrounding context and an approximate page number.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Segment:
    """One sentence with surrounding context for LLM annotation."""
    sentence_id: int
    text: str              # the sentence itself
    char_start: int        # absolute position in document
    char_end: int          # exclusive
    context_before: str    # 2-3 sentences before (empty for first)
    context_after: str     # 2-3 sentences after (empty for last)
    page_number: int = 0   # approximate page (0-based)
