"""
Inline formatting within block text.

_apply_all_inline applies bold/italic/mono markers and $...$ math wrapping
using sorted absolute-position actions (italic suppressed in display math,
bold/italic suppressed in headings and overlapping math). Co-locates the
Unicode->KaTeX symbol map _KATEX_SYMBOL_MAP with its sanitizer
_sanitize_for_katex.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, MarkerType, HEADING_LABELS


_KATEX_SYMBOL_MAP = {
    '∅': '\\emptyset',
    'Ω': '\\Omega',
    'σ': '\\sigma',
    'α': '\\alpha',
    'β': '\\beta',
    '∪': '\\cup',
    '∩': '\\cap',
    '⊆': '\\subseteq',
    '∈': '\\in',
    '∉': '\\notin',
    '⊂': '\\subset',
    '⊃': '\\supset',
    '⊇': '\\supseteq',
    '×': '\\times',
    '→': '\\rightarrow',
    '⇒': '\\Rightarrow',
    '∀': '\\forall',
    '∃': '\\exists',
    '¬': '\\neg',
    '∞': '\\infty',
}


def _sanitize_for_katex(text: str) -> str:
    """Replace Unicode math symbols with LaTeX names for KaTeX rendering.

    KaTeX can render LaTeX commands like \\Omega, \\emptyset, but does not
    recognize bare Unicode symbols like Ω, ∅ in math mode. This function
    converts those symbols to their LaTeX equivalents.

    Does NOT escape braces — that would break LaTeX commands like \\mathcal{F}.
    Braces in set notation should already be escaped as \\{ and \\} in the
    OCR output. If they're bare in span text, KaTeX will eat them, but that's
    better than breaking proper LaTeX commands.
    """
    for sym, latex in _KATEX_SYMBOL_MAP.items():
        text = text.replace(sym, latex)
    return text


def _apply_all_inline(
    block_text: str,
    block_start: int,
    block_label: StructuralLabel,
    metadata_markers: dict[int, list[Marker]],
    math_regions: list[tuple[int, int]],
    formula_text_map: dict[int, str] | None = None,
) -> str:
    """Apply all inline formatting (bold/italic/mono + math) to block text.

    Both types of inline markers use absolute char positions. By processing
    them together, we avoid position-offset issues that arise when one type
    is applied before the other (which shifts positions for the second pass).

    Math regions get $...$ wrapping. Bold/italic markers that overlap with
    math regions are suppressed (italic on math symbols is typesetting, not
    emphasis). Bold/italic in headings are suppressed.
    """
    if not metadata_markers and not math_regions:
        return block_text

    block_end = block_start + len(block_text)

    # Collect all inline markers (both formatting and math)
    # Build a sorted list of (abs_position, action) tuples
    actions: list[tuple[int, str]] = []  # (abs_pos, text_to_insert)

    # Math regions: wrap in $...$ and convert Unicode symbols to LaTeX
    # We don't replace the entire region text with latex_text from OCR
    # (which can contain fragments like "{\emptyset"). Instead, we wrap
    # the original text in $...$ and apply Unicode→LaTeX conversion inside.
    from .formula_extractor import unicode_to_latex
    for mstart, mend in math_regions:
        if block_start <= mstart and mend <= block_end:
            # Get the original text in this math region
            raw_text = block_text[mstart - block_start:mend - block_start]
            # Convert Unicode math symbols to LaTeX within the original text
            converted = unicode_to_latex(raw_text)
            # Wrap in $...$
            converted = _sanitize_for_katex(converted)
            actions.append((mstart, f"${converted}$"))
            actions.append((mend, ""))  # marker to skip original text up to mend

    # Formatting markers (bold/italic/mono)
    if metadata_markers:
        for pos, marker_list in metadata_markers.items():
            if block_start <= pos <= block_end:
                for m in marker_list:
                    # Suppress italic inside DISPLAY_MATH blocks
                    if block_label == StructuralLabel.DISPLAY_MATH:
                        if m.type in (MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                            continue
                    # Suppress bold/italic in headings
                    if block_label in HEADING_LABELS:
                        if m.type in (MarkerType.BOLD_OPEN, MarkerType.BOLD_CLOSE,
                                       MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                            continue
                    # Suppress italic that overlaps with math regions
                    if math_regions and m.type in (MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                        for mr_start, mr_end in math_regions:
                            if mr_start <= pos <= mr_end:
                                break  # suppress this italic marker
                        else:
                            # Not in a math region — keep it
                            marker_text = {
                                MarkerType.BOLD_OPEN: "**", MarkerType.BOLD_CLOSE: "**",
                                MarkerType.ITALIC_OPEN: "*", MarkerType.ITALIC_CLOSE: "*",
                                MarkerType.MONO_OPEN: "`", MarkerType.MONO_CLOSE: "`",
                            }.get(m.type, "")
                            actions.append((pos, marker_text))
                        continue  # already handled (either suppressed or appended)

                    marker_text = {
                        MarkerType.BOLD_OPEN: "**", MarkerType.BOLD_CLOSE: "**",
                        MarkerType.ITALIC_OPEN: "*", MarkerType.ITALIC_CLOSE: "*",
                        MarkerType.MONO_OPEN: "`", MarkerType.MONO_CLOSE: "`",
                    }.get(m.type, "")
                    actions.append((pos, marker_text))

    if not actions:
        return block_text

    # Sort actions by position. For same position:
    # - Math "skip-end" markers (empty string at mend) should come AFTER
    #   formatting markers at the same position, so formatting applies first
    # - Math "insert" markers should come BEFORE text at the same position
    actions.sort(key=lambda x: (x[0], 0 if x[1] else 1))

    # Build output by interleaving original text and inserted markers
    result: list[str] = []
    prev = block_start
    skip_until = -1  # for math regions: skip original text from prev to this

    for abs_pos, insert_text in actions:
        # Check if this is the skip-end of a math region
        if abs_pos == skip_until and not insert_text:
            prev = abs_pos
            skip_until = -1
            continue

        # Add original text between prev and this action's position
        # Skip any original text that falls within a math region
        # (prev was advanced past the math region when we inserted $...$)
        rel_prev = prev - block_start
        rel_pos = abs_pos - block_start
        if rel_pos > rel_prev:
            result.append(block_text[rel_prev:rel_pos])

        if insert_text:
            result.append(insert_text)
            # If this is a math-region insertion ($...$), skip the original
            # text from mstart to mend by advancing prev to mend
            for mstart, mend in math_regions:
                if abs_pos == mstart and insert_text.startswith("$"):
                    prev = mend  # skip original math text
                    skip_until = mend  # mark so the (mend, "") noop is handled
                    break
            else:
                prev = abs_pos
        else:
            prev = abs_pos

    # Append remaining text
    rel_prev = prev - block_start
    if rel_prev < len(block_text):
        result.append(block_text[rel_prev:])

    return "".join(result)
