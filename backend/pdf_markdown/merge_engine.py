"""
Merge metadata markers with LLM structural annotations into final Markdown.

Block-based approach: text is split into contiguous regions by structural label,
then each block is formatted as a unit. Paragraphs get single blank-line
separation; inline formatting is applied within blocks.

This module is a shim re-exporting the implementation, which lives in the
split modules: merge_text_map, merge_blocks, merge_inline, merge_helpers,
merge_spacing, merge_core.
"""

from __future__ import annotations

import logging

from .merge_blocks import (
    _HEADING_PREFIX,
    _extract_blocks,
    _find_formula_latex,
    _format_block,
)
from .merge_helpers import (
    _already_has_list_marker,
    _apply_inline_math_to_block,
    _collapse_line_wraps,
    _escape_list_trigger,
    _indent_lines,
    _starts_structural_block,
)
from .merge_inline import (
    _KATEX_SYMBOL_MAP,
    _apply_all_inline,
    _sanitize_for_katex,
)
from .merge_spacing import (
    _clean_inline_math_spacing,
    _clean_unicode_math,
    _fix_math_operator_spacing,
    _fix_merged_spacing,
    _hard_breaks,
    _looks_like_two_words,
    _normalize_whitespace,
)
from .merge_text_map import (
    STRUCTURAL_PRIORITY,
    _EXAMPLE_ITEM_PATTERN,
    _SUB_ITEM_PATTERN,
    _build_char_labels,
    _build_formula_text_map,
    _normalize_block_labels,
)
from .merge_core import merge_annotations

logger = logging.getLogger(__name__)
