"""
Build and normalize structural label maps over the source text.

Produces the formula char_start->LaTeX lookup map, the per-character
structural label map with inline-math region tracking, and normalizes block
labels (Example/Definition patterns forced to unordered_list_item, sub-item
nesting bumps). Co-locates the two label-detection regexes with their
consumer.
"""

from __future__ import annotations

import re

from .annotation_schema import StructuralLabel

# Priority order for structural labels. Applied in this order so
# higher-priority labels cannot be overwritten by lower-priority ones.
STRUCTURAL_PRIORITY = [
    StructuralLabel.CODE_BLOCK,
    StructuralLabel.BLOCKQUOTE,
    StructuralLabel.ORDERED_LIST_ITEM,
    StructuralLabel.UNORDERED_LIST_ITEM,
    StructuralLabel.HEADING_1,
    StructuralLabel.HEADING_2,
    StructuralLabel.HEADING_3,
    StructuralLabel.HEADING_4,
    StructuralLabel.DISPLAY_MATH,
]


def _build_formula_text_map(formula_spans: list[LabeledSpan]) -> dict[int, str]:
    """Build a map from char_start position to latex_text for DISPLAY_MATH formulas only.

    Only DISPLAY_MATH formula spans need OCR LaTeX lookup — these are rendered
    as $$ blocks.  MATH (inline) formula spans use unicode_to_latex instead
    of this map, so including them would cause DISPLAY_MATH blocks to pick up
    partial inline LaTeX like "{\\emptyset" from a MATH span that overlaps.
    """
    result: dict[int, str] = {}
    for fs in formula_spans:
        if fs.latex_text and fs.label == StructuralLabel.DISPLAY_MATH:
            result[fs.char_start] = fs.latex_text
    return result


def _build_char_labels(
    text: str,
    llm_annotations: list[SentenceAnnotation],
    formula_spans: list[LabeledSpan],
) -> tuple[dict[int, StructuralLabel], list[tuple[int, int]]]:
    """Per-character structural label map and inline math region list.

    Returns (char_labels, math_regions) where:
    - char_labels maps each character to its structural label (paragraph,
      heading, list item, display math, etc.)
    - math_regions is a list of (char_start, char_end) pairs for inline
      MATH regions that should be treated as positional markers, not blocks.

    Inline MATH does NOT change the structural label — it's tracked
    separately so it can be injected as $...$ markers within paragraphs
    and list items. Only DISPLAY_MATH overrides the structural label.
    """
    char_labels: dict[int, StructuralLabel] = {}
    for i in range(len(text)):
        char_labels[i] = StructuralLabel.PARAGRAPH

    # Apply LLM labels in priority order — only overwrite PARAGRAPH positions
    for label_type in STRUCTURAL_PRIORITY:
        for sent_ann in llm_annotations:
            for ls in sent_ann.labels:
                if ls.label != label_type:
                    continue
                for i in range(ls.char_start, min(ls.char_end, len(text))):
                    if char_labels[i] == StructuralLabel.PARAGRAPH:
                        char_labels[i] = ls.label

    # Collect inline MATH regions (tracked separately, NOT applied to char_labels)
    math_regions: list[tuple[int, int]] = []
    # Apply DISPLAY_MATH labels — these override any label since they
    # genuinely need their own block with $$...$$
    for fs in formula_spans:
        if fs.label == StructuralLabel.DISPLAY_MATH:
            for i in range(fs.char_start, min(fs.char_end, len(text))):
                char_labels[i] = StructuralLabel.DISPLAY_MATH
        elif fs.label == StructuralLabel.MATH:
            # Trim leading/trailing whitespace and set-notation braces from
            # math region boundaries.  Formula spans inherit span boundaries
            # which can include adjacent whitespace (e.g. "∅ ") and braces
            # (e.g. "{∅") that are set notation, not LaTeX content.
            # Braces at boundaries stay outside the $...$ wrapper as regular
            # text, which renders correctly in browsers.
            # Also trim trailing ASCII letters/digits that are not math symbols.
            # Spans like "∈S" have high math density but "S" at the end is
            # plain text, not LaTeX.  It should stay outside $...$ as regular
            # text: "$\in$ S" instead of "$\inS$" (which KaTeX can't parse).
            start = fs.char_start
            end = min(fs.char_end, len(text))
            # Trim leading whitespace/punctuation/braces
            while start < end and text[start] in (' ', '\n', '{', '}', ',', '.', ';', ':'):
                start += 1
            # Trim trailing whitespace/punctuation/braces
            while end > start and text[end - 1] in (' ', '\n', '{', '}', ',', '.', ';', ':'):
                end -= 1
            if start < end:
                math_regions.append((start, end))

    # Merge overlapping/adjacent math regions into continuous spans
    if math_regions:
        math_regions.sort()
        merged: list[tuple[int, int]] = []
        for start, end in math_regions:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        math_regions = merged

    return char_labels, math_regions


# Patterns that should be treated as unordered list items regardless of LLM label
_EXAMPLE_ITEM_PATTERN = re.compile(
    r'^Example\s+\d+[:\.\s]|'
    r'^Definition[:\.\s]|'
    r'^Remark[:\.\s]|'
    r'^Note[:\.\s]|'
    r'^Theorem\s*\d*[:\.\s]|'
    r'^Lemma\s*\d*[:\.\s]|'
    r'^Corollary\s*\d*[:\.\s]|'
    r'^Proposition\s*\d*[:\.\s]',
    re.IGNORECASE,
)

# Sub-item markers that typically appear at nesting >= 2 in academic documents
_SUB_ITEM_PATTERN = re.compile(
    r'^\([a-z]\)\s|'       # (a), (b), (c)
    r'^[ivxlcdm]+[\.\)]\s', # i., ii., iii., iv.
    re.IGNORECASE,
)


def _normalize_block_labels(blocks: list[dict]) -> list[dict]:
    """Normalize block labels and nesting levels for consistency.

    Three corrections:
    1. Example/Definition patterns → always unordered_list_item
    2. Sub-item markers (i., ii., iii., (a), (b), (c)) at low nesting
       → bump nesting based on nearest preceding higher-level list item
    3. Sub-item markers at nesting=1 preceded by a mid-level list item
       → inherit nesting = preceding.nesting + 1
    """
    for i, block in enumerate(blocks):
        stripped = block["text"].strip()

        # --- Fix 1: Normalize Example/Definition labels ---
        if _EXAMPLE_ITEM_PATTERN.match(stripped):
            nesting = 1
            for j in range(i - 1, -1, -1):
                prev = blocks[j]
                if prev["label"] in (StructuralLabel.ORDERED_LIST_ITEM,
                                      StructuralLabel.UNORDERED_LIST_ITEM):
                    nesting = prev.get("nesting_level", 1)
                    break
            block["label"] = StructuralLabel.UNORDERED_LIST_ITEM
            block["nesting_level"] = nesting

        # --- Fix 2: Bump nesting for under-labeled sub-items ---
        # i., ii., iii. and (a), (b), (c) at nesting_level=1 are almost
        # always wrong in academic documents — they're sub-items under
        # numbered lists (1., 2., 3.) or lettered lists, not top-level.
        # Only fix nesting=1; nesting=2+ is likely already correct.
        if (block["label"] in (StructuralLabel.ORDERED_LIST_ITEM,
                                StructuralLabel.UNORDERED_LIST_ITEM)
            and block.get("nesting_level", 0) == 1
            and _SUB_ITEM_PATTERN.match(stripped)):
            # Scan backwards for nearest preceding list item
            for j in range(i - 1, -1, -1):
                prev = blocks[j]
                if prev["label"] in (StructuralLabel.ORDERED_LIST_ITEM,
                                      StructuralLabel.UNORDERED_LIST_ITEM):
                    prev_nesting = prev.get("nesting_level", 1)
                    block["nesting_level"] = prev_nesting + 1
                    break

    return blocks
