"""
Fragment mixin: per-sentence markdown fragments for SSE streaming.

OCR-latex lookup, inline $...$ math injection, the sentence-fragment
renderer, and the sentence_result SSE message builder. Called via self
by the annotation stage.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, SentenceAnnotation, SSEMessage
from .streaming import sentence_result


class FragmentMixin:
    """Per-sentence markdown fragment rendering stage of the PDF pipeline."""

    def _find_formula_latex(self, start: int, end: int) -> str | None:
        """Look up OCR LaTeX for a formula region within [start, end)."""
        for f in self.formulas:
            if start <= f.char_start < end and f.latex_text:
                return f.latex_text
        return None

    def _inject_inline_math(self, text: str, abs_start: int, abs_end: int) -> str:
        """Inject $...$ markers around inline math regions within a text range.

        Used by _compute_sentence_fragment for SSE streaming. Analogous to
        merge_engine's _apply_inline_math_to_block but operates on a
        sentence-level range.
        """
        from .merge_engine import _sanitize_for_katex, _clean_unicode_math

        # Find inline MATH formula spans that fall within this sentence range
        math_regions = []
        for f in self.formulas:
            if f.label == StructuralLabel.MATH and abs_start <= f.char_start and f.char_end <= abs_end:
                math_regions.append((f.char_start, f.char_end, f.latex_text))

        if not math_regions:
            return text

        # Sort and inject $...$ markers (build from end to avoid offset shifts)
        math_regions.sort(key=lambda x: x[0])
        result_parts: list[str] = []
        prev_rel = 0  # relative position within text

        for m_start, m_end, latex in math_regions:
            # Convert absolute positions to relative within text
            rel_start = m_start - abs_start
            rel_end = m_end - abs_start
            if rel_start < 0 or rel_end > len(text):
                continue
            if rel_start > prev_rel:
                result_parts.append(text[prev_rel:rel_start])
            if latex:
                result_parts.append(f"${_sanitize_for_katex(latex)}$")
            else:
                raw = text[rel_start:rel_end]
                result_parts.append(f"${_sanitize_for_katex(_clean_unicode_math(raw))}$")
            prev_rel = rel_end

        if prev_rel < len(text):
            result_parts.append(text[prev_rel:])

        return "".join(result_parts)

    def _compute_sentence_fragment(self, sent_ann: SentenceAnnotation) -> str:
        """Compute a per-sentence markdown fragment for SSE streaming.

        Produces just the sentence's text formatted according to its labels
        and inline markers, without calling merge_annotations() on the full
        document text.
        """
        from .annotation_schema import HEADING_LABELS, HEADING_LEVEL, MarkerType
        from .merge_engine import _already_has_list_marker, _hard_breaks, _sanitize_for_katex, _clean_unicode_math, _fix_math_operator_spacing

        sent_text = self.text[sent_ann.char_start:sent_ann.char_end]

        # Apply inline markers within the sentence range
        inline_result: list[str] = []
        markers_at_pos: list[tuple[int, MarkerType]] = []
        primary_label = sent_ann.labels[0].label if sent_ann.labels else StructuralLabel.PARAGRAPH

        for pos, marker_list in self.metadata_markers.items():
            if sent_ann.char_start <= pos <= sent_ann.char_end:
                rel_pos = pos - sent_ann.char_start
                for m in marker_list:
                    if primary_label in (StructuralLabel.MATH, StructuralLabel.DISPLAY_MATH):
                        if m.type in (MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                            continue
                    if primary_label in HEADING_LABELS:
                        if m.type in (MarkerType.BOLD_OPEN, MarkerType.BOLD_CLOSE,
                                       MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                            continue
                    markers_at_pos.append((rel_pos, m.type))

        markers_at_pos.sort(key=lambda x: (x[0], 0 if x[1].value.endswith("_open") else 1))

        prev = 0
        for rel_pos, marker_type in markers_at_pos:
            if rel_pos > prev:
                inline_result.append(sent_text[prev:rel_pos])
            prev = rel_pos
            marker_text = {
                MarkerType.BOLD_OPEN: "**", MarkerType.BOLD_CLOSE: "**",
                MarkerType.ITALIC_OPEN: "*", MarkerType.ITALIC_CLOSE: "*",
                MarkerType.MONO_OPEN: "`", MarkerType.MONO_CLOSE: "`",
            }.get(marker_type, "")
            inline_result.append(marker_text)
        inline_result.append(sent_text[prev:])
        inline_text = "".join(inline_result)

        nesting = sent_ann.labels[0].nesting_level if sent_ann.labels else 0

        if primary_label in HEADING_LABELS:
            level = HEADING_LEVEL.get(primary_label, 1)
            return f"\n\n{'#' * level} {inline_text.strip()}\n"
        elif primary_label == StructuralLabel.ORDERED_LIST_ITEM:
            # Streaming: each fragment is independent, so use paragraph format
            # with indentation to approximate the grouped layout
            import re as _re
            indent = "  " * max(0, nesting - 1)
            escaped = _re.sub(r'^(\d+)\.', r'\1\\.', inline_text.strip())
            return f"\n\n{_hard_breaks(indent + escaped)}"
        elif primary_label == StructuralLabel.UNORDERED_LIST_ITEM:
            indent = "  " * max(0, nesting - 1)
            return f"\n\n{_hard_breaks(indent + '- ' + inline_text.strip())}"
        elif primary_label == StructuralLabel.BLOCKQUOTE:
            return f"\n\n> {inline_text.strip()}\n"
        elif primary_label == StructuralLabel.CODE_BLOCK:
            return f"\n\n```\n{inline_text.strip()}\n```\n"
        elif primary_label == StructuralLabel.DISPLAY_MATH:
            latex = self._find_formula_latex(sent_ann.char_start, sent_ann.char_end)
            if latex:
                return f"\n\n$$\n{_sanitize_for_katex(latex)}\n$$"
            # No valid OCR LaTeX — output as regular text
            return f"\n\n{_hard_breaks(_clean_unicode_math(inline_text.strip()))}"
        else:
            # Paragraph or list item — inject inline math as $...$ markers
            math_text = self._inject_inline_math(inline_text, sent_ann.char_start, sent_ann.char_end)
            # Paragraph — needs \n\n separator like merge_engine._format_block
            return f"\n\n{_hard_breaks(math_text.strip())}"

    def _build_sentence_result(self, sent_ann: SentenceAnnotation) -> SSEMessage:
        """Build the per-sentence SSE result message for streaming."""
        sent_text = self.text[sent_ann.char_start:sent_ann.char_end]
        labels_json = [
            {
                "label": ls.label.value,
                "char_start": ls.char_start,
                "char_end": ls.char_end,
                "nesting_level": ls.nesting_level,
                "confidence": ls.confidence,
            }
            for ls in sent_ann.labels
        ]

        # Compute per-sentence fragment (NOT full-document merge)
        fragment = self._compute_sentence_fragment(sent_ann)

        return sentence_result(
            sent_ann.sentence_id,
            fragment,
            sent_text,
            labels_json,
        )
