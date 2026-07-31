"""
Metadata/formatting suppression mixin.

Removes italic markers on short math-like spans in math-heavy documents.
Called via self from both run() and run_streaming().
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MetadataMixin:
    """Metadata marker suppression stage of the PDF pipeline."""

    def _suppress_formatting_if_math_heavy(self) -> None:
        """Remove italic markers around single math symbols (Ω, σ, F, etc).

        In math PDFs, italic on single-letter variables is typesetting convention,
        not emphasis. But italic on multi-word phrases like "measurable event"
        IS semantic emphasis — preserve those.

        Only suppress italic when the marked text is a short math-like span
        (single char, or a few chars with high math density). Bold is always
        preserved since bold in math PDFs is rare and meaningful when present.
        """
        if not self.text or not self.metadata_markers:
            return

        from .formula_extractor import math_symbol_density
        text_density = math_symbol_density(self.text)
        if text_density < 0.01:
            return  # Not a math-heavy document

        from .annotation_schema import MarkerType
        removed = 0
        for pos in list(self.metadata_markers.keys()):
            original = self.metadata_markers[pos]
            filtered = []
            for m in original:
                # Only suppress ITALIC, never suppress BOLD
                if m.type in (MarkerType.ITALIC_OPEN, MarkerType.ITALIC_CLOSE):
                    # Check what text this italic wraps — get the span text at this position
                    span_text = ""
                    for s in self.spans:
                        if s.char_start <= pos <= s.char_end:
                            span_text = s.text
                            break
                    # Suppress italic only if text is short and math-like
                    if len(span_text.strip()) <= 2 or math_symbol_density(span_text) >= 0.5:
                        removed += 1
                        continue  # suppress this italic marker
                filtered.append(m)
            if filtered:
                self.metadata_markers[pos] = filtered
            else:
                del self.metadata_markers[pos]

        logger.info(
            f"Math-heavy document detected (density={text_density:.3f}), "
            f"removed {removed} italic markers"
        )
