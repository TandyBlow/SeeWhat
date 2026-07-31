"""
Public entry point merge_annotations().

Orchestrates formula-map building, char-label map building, block extraction +
label normalization, list-group assembly (continuation paragraphs/display-math
under list items), per-block inline formatting, and the four whitespace/math
post-processing passes. Sits at the top of the import DAG — imports every other
split module, none import it back.
"""

from __future__ import annotations

import re

from .annotation_schema import StructuralLabel
from .merge_blocks import _extract_blocks, _format_block, _find_formula_latex
from .merge_helpers import _already_has_list_marker, _collapse_line_wraps, _escape_list_trigger, _indent_lines, _starts_structural_block
from .merge_inline import _apply_all_inline, _sanitize_for_katex
from .merge_spacing import _clean_inline_math_spacing, _clean_unicode_math, _fix_math_operator_spacing, _hard_breaks, _normalize_whitespace
from .merge_text_map import _build_char_labels, _build_formula_text_map, _normalize_block_labels


def merge_annotations(
    text: str,
    metadata_markers: dict[int, list[Marker]],
    llm_annotations: list[SentenceAnnotation],
    formula_spans: list[LabeledSpan] | None = None,
) -> str:
    """Merge all annotations into final Markdown text.

    Nested ordered list items (a)(b)(c) and i.ii.iii. are formatted as a single
    continuous text block with hard line breaks and indentation — like the original
    document layout.  This avoids markdown list syntax which breaks rendering of
    custom markers.  Other block types (headings, paragraphs, math, code) use
    standard markdown formatting.
    """
    if formula_spans is None:
        formula_spans = []

    if not text:
        return ""

    # Build formula LaTeX lookup map
    formula_text_map = _build_formula_text_map(formula_spans)

    # Build character-level label map and inline math regions
    char_labels, global_math_regions = _build_char_labels(text, llm_annotations, formula_spans)

    # Extract blocks (inline MATH absorbed into surrounding blocks)
    blocks = _extract_blocks(text, char_labels, llm_annotations, global_math_regions)

    # Normalize Example/Definition labels for consistency
    blocks = _normalize_block_labels(blocks)

    # Format blocks — consecutive ordered_list_item blocks are grouped into
    # one continuous text block with hard breaks and indentation.
    output_parts: list[str] = []
    block_idx = 0

    while block_idx < len(blocks):
        block = blocks[block_idx]

        if block["label"] in (StructuralLabel.ORDERED_LIST_ITEM, StructuralLabel.UNORDERED_LIST_ITEM):
            # Collect all consecutive list items (both ordered and unordered)
            # into one group — mixed hierarchies like (a)(b)(c) + Examples
            # must stay together to preserve visual nesting.
            # Also include adjacent PARAGRAPH/DISPLAY_MATH blocks that are
            # continuation content of a list item (e.g., formulas or
            # continuation text under "Example 1:" that the LLM labeled
            # as separate blocks).
            group_lines: list[str] = []
            current_nesting = block.get("nesting_level", 1)
            j = block_idx
            while j < len(blocks):
                j_block = blocks[j]
                j_label = j_block["label"]

                # Core list items — always include
                if j_label in (StructuralLabel.ORDERED_LIST_ITEM, StructuralLabel.UNORDERED_LIST_ITEM):
                    j_text = _apply_all_inline(
                        j_block["text"], j_block["char_start"],
                        j_block["label"], metadata_markers,
                        j_block.get("math_regions", []),
                        formula_text_map,
                    )
                    j_nesting = j_block.get("nesting_level", 0)
                    j_indent = "  " * max(0, j_nesting - 1)
                    # Collapse PDF line wraps within the item text (all breaks for grouped content)
                    stripped = _collapse_line_wraps(j_text, collapse_paragraphs=True).strip()
                    if j_label == StructuralLabel.UNORDERED_LIST_ITEM:
                        if not _already_has_list_marker(stripped) and not stripped.startswith("- "):
                            group_lines.append(_indent_lines(stripped, j_indent, "- "))
                        else:
                            group_lines.append(_indent_lines(stripped, j_indent))
                    else:
                        group_lines.append(_indent_lines(stripped, j_indent))
                    current_nesting = j_nesting
                    j += 1
                    continue

                # Continuation content: PARAGRAPH or DISPLAY_MATH that
                # appears right after a list item and doesn't start with
                # a structural marker (heading, list prefix, etc.)
                # Include it with the same indentation as the preceding item
                # so formulas and continuation text stay visually nested.
                if j_label in (StructuralLabel.PARAGRAPH, StructuralLabel.DISPLAY_MATH):
                    j_text = _apply_all_inline(
                        j_block["text"], j_block["char_start"],
                        j_block["label"], metadata_markers,
                        j_block.get("math_regions", []),
                        formula_text_map,
                    )
                    # Collapse PDF line wraps for continuation text too (all breaks for grouped content)
                    stripped = _collapse_line_wraps(j_text, collapse_paragraphs=True).strip()

                    # Don't include if it starts with a heading or list marker
                    # (those are structural breaks, not continuation)
                    if _starts_structural_block(stripped):
                        break

                    # Include as continuation text at the same indent level
                    cont_indent = "  " * max(0, current_nesting - 1)

                    if j_label == StructuralLabel.DISPLAY_MATH:
                        latex = _find_formula_latex(j_block["char_start"], j_block["char_end"], formula_text_map)
                        if latex:
                            group_lines.append(cont_indent + "$$ " + _sanitize_for_katex(latex) + " $$")
                        else:
                            group_lines.append(cont_indent + _clean_unicode_math(stripped))
                    else:
                        group_lines.append(cont_indent + stripped)
                    j += 1
                    continue

                # Any other block type (heading, blockquote, code_block) breaks the group
                break

            # Assemble into one continuous text block with \n line breaks
            assembled = "\n".join(group_lines)
            # Escape leading N. triggers so marked.js doesn't parse as list
            assembled = _escape_list_trigger(assembled)
            # Convert all \n to hard breaks (  \n) for markdown rendering
            assembled = _hard_breaks(assembled)
            output_parts.append(f"\n\n{assembled}")

            block_idx = j  # skip past all the grouped blocks
        else:
            # Apply all inline formatting (bold/italic + math) for non-list blocks
            block_text = _apply_all_inline(
                block["text"], block["char_start"],
                block["label"], metadata_markers,
                block.get("math_regions", []),
                formula_text_map,
            )
            # Collapse PDF line wraps for paragraph blocks —
            # produces flowing text instead of hard-break per PDF line.
            # \n→space is a 1:1 replacement so positions stay valid.
            if block["label"] == StructuralLabel.PARAGRAPH:
                block_text = _collapse_line_wraps(block_text)
            block["text"] = block_text

            list_counter: dict[int, int] = {}
            formatted = _format_block(block, list_counter, formula_text_map)
            output_parts.append(formatted)
            block_idx += 1

    result = "".join(output_parts)

    # Post-process: normalize whitespace
    result = _normalize_whitespace(result)

    # Post-process: fix intra-span math spacing where union/intersection
    # operators are glued to braces without a space (e.g. ∪{ → ∪ {)
    result = _fix_math_operator_spacing(result)

    # Post-process: clean up $...$ wrapping — remove leading/trailing spaces
    # inside $ delimiters and fix LaTeX command spacing
    result = _clean_inline_math_spacing(result)

    # Post-process: add space between closing $ and following letter/digit
    # When math regions are trimmed, characters that were adjacent to the
    # symbol become directly after $, e.g. "$\in$S" → "$\in$ S"
    # (this is for characters OUTSIDE $...$, not inside)
    result = re.sub(r'\$([^$]+)\$([a-zA-Z0-9])', r'$\1$ \2', result)

    # Trim leading/trailing whitespace
    result = result.strip()

    return result
