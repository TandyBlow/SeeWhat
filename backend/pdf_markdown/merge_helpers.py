"""
Small reusable text/line helpers used across the merge pipeline.

List-marker detection (_already_has_list_marker), structural-block break
detection (_starts_structural_block), indentation (_indent_lines), PDF
line-wrap collapsing (_collapse_line_wraps), markdown list-trigger escaping
(_escape_list_trigger), and the legacy, currently-unused
_apply_inline_math_to_block (must be preserved).
"""

from __future__ import annotations

import re

from .merge_inline import _sanitize_for_katex
from .merge_spacing import _clean_unicode_math


def _already_has_list_marker(text: str) -> bool:
    """Check if text already starts with a list number/bullet prefix."""
    stripped = text.strip()
    # "1.", "2.", "1)", "(1)", "[1]"
    if re.match(r'^[\(\[]?[\d]+[\.\)\]\s]', stripped):
        return True
    # "(1) " or "(2) "
    if re.match(r'^\([\d]+\)\s', stripped):
        return True
    # "(a) ", "(b) ", "(i) " — parenthesized letter/roman numeral
    if re.match(r'^\([a-z]\)\s', stripped):
        return True
    # Roman numerals: "i.", "ii.", "iv.", etc.
    if re.match(r'^[ivxlcdm]+[\.\)]\s', stripped, re.IGNORECASE):
        return True
    # Letter bullets: "a.", "b.", "a) "
    if re.match(r'^[a-z][\.\)]\s', stripped):
        return True
    return False


def _starts_structural_block(text: str) -> bool:
    """Check if text starts with a structural marker that breaks a list group.

    Returns True if the text begins with a heading (#), list prefix (1., (a),
    -), Example/Definition marker, or other structural signal — indicating
    it's NOT continuation content within a list.
    """
    stripped = text.strip()
    if not stripped:
        return True
    # Markdown heading
    if stripped.startswith('#'):
        return True
    # Already a list marker
    if _already_has_list_marker(stripped):
        return True
    # Markdown bullet
    if stripped.startswith('- ') or stripped.startswith('* '):
        return True
    # Example/Definition/Remark/Note/Theorem headings
    if re.match(r'^Example\s+\d+', stripped, re.IGNORECASE):
        return True
    if re.match(r'^(Definition|Remark|Note|Theorem|Lemma|Corollary|Proposition)\s*\d*', stripped, re.IGNORECASE):
        return True
    return False


def _indent_lines(text: str, indent: str, first_line_prefix: str = "") -> str:
    """Apply indentation to each line of text, with optional prefix on first line.

    Ensures multi-line list item text stays visually nested on every line,
    not just the first line.
    """
    lines = text.split('\n')
    result: list[str] = []
    for i, line in enumerate(lines):
        if i == 0:
            result.append(indent + first_line_prefix + line)
        else:
            result.append(indent + line)
    return '\n'.join(result)


def _collapse_line_wraps(text: str, collapse_paragraphs: bool = False) -> str:
    """Collapse single \\n (PDF line wraps) to spaces within text.

    PDF line breaks like "especially\\nprobability theory" are layout artifacts,
    not semantic breaks. Collapsing them produces natural flowing text.

    Args:
        collapse_paragraphs: If True, convert \\n\\n paragraph breaks to \\n
            (tight line breaks) instead of preserving them as \\n\\n gaps.
            Used for grouped list content where paragraph gaps create
            unwanted visual spacing between formula/description lines.
            Real structure (like formulas on separate lines) is preserved
            as single line breaks, not merged into flowing text.
    """
    if '\n' not in text:
        return text
    # Split on paragraph breaks, collapse line wraps within each paragraph
    paragraphs = text.split('\n\n')
    collapsed = []
    for para in paragraphs:
        collapsed.append(para.replace('\n', ' '))
    if collapse_paragraphs:
        # Rejoin with \n (tight line break) — preserves structure
        # (formula/description on separate lines) but avoids \n\n gaps
        return '\n'.join(collapsed)
    else:
        # Preserve paragraph breaks as \n\n
        return '\n\n'.join(collapsed)


def _escape_list_trigger(text: str) -> str:
    """Escape leading N. pattern (like 1., 2.) to prevent markdown list parsing.

    Nested list structures are formatted as a single text block with hard breaks
    and indentation, not as separate markdown list items.  Escaping the top-level
    number prevents marked.js from incorrectly splitting the block into list items.
    """
    return re.sub(r'^(\d+)\.', r'\1\\.', text)


def _apply_inline_math_to_block(
    block_text: str,
    block_start: int,
    math_regions: list[tuple[int, int]],
    formula_text_map: dict[int, str] | None = None,
) -> str:
    """Inject $...$ markers around inline math regions within a block.

    Math regions are (char_start, char_end) absolute positions that
    fall within [block_start, block_start + len(block_text)]. For
    each region, the original text is replaced with $latex$ or
    $unicode$ depending on whether OCR produced LaTeX.
    """
    if not math_regions or not formula_text_map:
        return block_text

    block_end = block_start + len(block_text)

    # Filter math regions that actually fall within this block
    regions_in_block = [
        (s, e) for s, e in math_regions
        if block_start <= s and e <= block_end
    ]
    if not regions_in_block:
        return block_text

    # Build replacement map: for each region, compute what to insert
    replacements: list[tuple[int, int, str]] = []  # (abs_start, abs_end, replacement_text)
    for mstart, mend in regions_in_block:
        # Look up LaTeX from formula_text_map
        latex = None
        for fs_start, fs_latex in formula_text_map.items():
            if mstart <= fs_start < mend and fs_latex:
                latex = fs_latex
                break

        if latex:
            replacements.append((mstart, mend, f"${_sanitize_for_katex(latex)}$"))
        else:
            # No LaTeX — wrap Unicode math symbols in $...$
            raw_text = block_text[mstart - block_start:mend - block_start]
            cleaned = _clean_unicode_math(raw_text)
            replacements.append((mstart, mend, f"${_sanitize_for_katex(cleaned)}$"))

    # Sort replacements by start position (reverse to build from end)
    replacements.sort(key=lambda x: x[0])

    # Build output by splicing replacements into block_text
    result: list[str] = []
    prev = block_start
    for abs_start, abs_end, replacement in replacements:
        rel_start = abs_start - block_start
        rel_prev = prev - block_start
        if rel_start > rel_prev:
            result.append(block_text[rel_prev:rel_start])
        result.append(replacement)
        prev = abs_end
    # Append remaining text after last replacement
    rel_prev = prev - block_start
    if rel_prev < len(block_text):
        result.append(block_text[rel_prev:])

    return "".join(result)
