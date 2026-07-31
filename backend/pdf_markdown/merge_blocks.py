"""
Split text into contiguous blocks by structural label and format each block.

_extract_blocks splits text by structural label; _format_block formats each
block into markdown (headings via _HEADING_PREFIX, ordered/unordered lists,
blockquote, code fence, $$ display math or plain text, paragraphs). Also hosts
_find_formula_latex, the OCR-LaTeX lookup used by both _format_block and
merge_core's list-group continuation branch.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, HEADING_LABELS
from .merge_inline import _sanitize_for_katex
from .merge_spacing import _hard_breaks, _clean_unicode_math

_HEADING_PREFIX = {StructuralLabel.HEADING_1: "# ",
                   StructuralLabel.HEADING_2: "## ",
                   StructuralLabel.HEADING_3: "### ",
                   StructuralLabel.HEADING_4: "#### "}


def _extract_blocks(
    text: str,
    char_labels: dict[int, StructuralLabel],
    llm_annotations: list[SentenceAnnotation],
    math_regions: list[tuple[int, int]] | None = None,
) -> list[dict]:
    """Split text into contiguous blocks of the same structural label.

    Inline MATH (single symbols like σ, Ω, ∅) is NOT treated as a
    separate block. Instead, MATH characters are absorbed into the
    surrounding block (paragraph, list item, heading) and tracked as
    `math_regions` sub-annotations within that block. Only DISPLAY_MATH
    creates its own block.

    Returns list of dicts with: label, text, char_start, char_end,
    nesting_level, math_regions.
    """
    if not text:
        return []

    if math_regions is None:
        math_regions = []

    # Find all label transition points
    transitions: list[int] = [0]
    prev_label = char_labels.get(0, StructuralLabel.PARAGRAPH)

    for i in range(1, len(text)):
        current = char_labels.get(i, StructuralLabel.PARAGRAPH)
        if current != prev_label:
            transitions.append(i)
            prev_label = current
    transitions.append(len(text))

    # Build nesting lookup from LLM annotations
    nesting_map: dict[StructuralLabel, dict[int, int]] = {}
    for sent_ann in llm_annotations:
        for ls in sent_ann.labels:
            nesting_map.setdefault(ls.label, {})[ls.char_start] = ls.nesting_level

    blocks: list[dict] = []
    for j in range(len(transitions) - 1):
        start = transitions[j]
        end = transitions[j + 1]
        label = char_labels.get(start, StructuralLabel.PARAGRAPH)

        chunk = text[start:end]

        # Whitespace-only blocks at label transitions carry paragraph breaks
        # (\n\n). Merge them into the preceding block instead of dropping them,
        # so that "could be\n\n" + "F = {..." preserves the paragraph gap.
        if not chunk.strip():
            if blocks and '\n' in chunk:
                blocks[-1]["text"] += chunk
                # Only extend math_regions with regions that fall within
                # the newly-added whitespace range, NOT the full block range
                # (the existing math_regions already cover the original range)
                old_end = blocks[-1]["char_end"]
                blocks[-1]["char_end"] = end
                new_math = [r for r in math_regions if old_end <= r[0] and r[1] <= end]
                if new_math:
                    blocks[-1]["math_regions"].extend(new_math)
            continue

        # Collect inline MATH regions that fall within this block's range
        block_math = [r for r in math_regions if start <= r[0] and r[1] <= end]

        # Get nesting level for this label at this position
        nesting = 0
        label_nests = nesting_map.get(label, {})
        for nstart, nlevel in sorted(label_nests.items()):
            if nstart <= start:
                nesting = nlevel

        blocks.append({
            "label": label,
            "text": chunk,
            "char_start": start,
            "char_end": end,
            "nesting_level": nesting,
            "math_regions": block_math,
        })

    return blocks


def _find_formula_latex(block_start: int, block_end: int,
                        formula_text_map: dict[int, str] | None) -> str | None:
    """Look up OCR-derived LaTeX for a math block by checking formula char_starts."""
    if not formula_text_map:
        return None
    # Check if any formula span starts within this block
    for fs_start, latex in formula_text_map.items():
        if block_start <= fs_start < block_end and latex:
            return latex
    return None


def _format_block(block: dict, list_counter: dict[int, int],
                  formula_text_map: dict[int, str] | None = None) -> str:
    """Format a single block into markdown."""
    label = block["label"]
    text = block["text"]
    nesting = block["nesting_level"]

    # Clean whitespace within block
    text = text.strip()
    if not text:
        return ""

    # Heading
    if label in HEADING_LABELS:
        prefix = _HEADING_PREFIX.get(label, "")
        return f"\n\n{prefix}{text}\n"

    # Ordered list — always use markdown numbering for proper rendering.
    # Custom markers (a), i., ii. etc. are kept in the text content.
    if label == StructuralLabel.ORDERED_LIST_ITEM:
        # Markdown sub-lists need 3-space indent per nesting level
        # (aligns with parent content, not the marker)
        indent = "   " * max(0, nesting - 1)
        idx = list_counter.get(nesting, 1)
        list_counter[nesting] = idx + 1
        # Clean deeper counters
        for k in list(list_counter.keys()):
            if k > nesting:
                del list_counter[k]
        return f"\n{indent}{idx}. {_hard_breaks(text)}"

    # Unordered list
    if label == StructuralLabel.UNORDERED_LIST_ITEM:
        indent = "   " * max(0, nesting - 1)
        return f"\n{indent}- {_hard_breaks(text)}"

    # Blockquote
    if label == StructuralLabel.BLOCKQUOTE:
        lines = text.split('\n')
        quoted = '\n'.join(f"> {line}" for line in lines if line.strip())
        return f"\n\n{quoted}\n"

    # Code block
    if label == StructuralLabel.CODE_BLOCK:
        return f"\n\n```\n{text}\n```\n"

    # Display math — ONLY use $$ when OCR produced valid LaTeX
    if label == StructuralLabel.DISPLAY_MATH:
        latex = _find_formula_latex(block["char_start"], block["char_end"], formula_text_map)
        if latex:
            return f"\n\n$$\n{_sanitize_for_katex(latex)}\n$$"
        # No valid OCR LaTeX — output as regular text with paragraph break
        return f"\n\n{_hard_breaks(_clean_unicode_math(text))}"

    # Default: paragraph — preserve PDF line breaks as markdown hard breaks
    return f"\n\n{_hard_breaks(text)}"
