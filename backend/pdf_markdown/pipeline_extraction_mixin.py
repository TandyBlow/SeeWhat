"""
Extraction stage mixin: single-pass spans-based text extraction with OCR
fallback detection.

Part of the FullPipeline split. Methods are called via self by run() and
run_streaming().
"""

from __future__ import annotations

import logging

from .span_extractor import extract_spans, spans_to_text

logger = logging.getLogger(__name__)


class ExtractionMixin:
    """Text/span extraction stage of the PDF pipeline."""

    def _extract_and_check(self) -> bool:
        """Extract spans-based text and check OCR need in a single pass.

        Uses spans as the single source of truth for text. Text is
        reconstructed via spans_to_text() to maintain position alignment.
        Returns needs_ocr flag.
        """
        # Try span extraction first (single PDF open)
        try:
            all_spans = extract_spans(self.file_path)
            filtered_spans = self._filter_spans(all_spans)
            if filtered_spans:
                self.text = spans_to_text(filtered_spans)
                self.spans = filtered_spans
            else:
                self.text = ""
                self.spans = []
        except Exception as e:
            logger.warning(f"Span extraction failed: {e}")
            self.text = ""
            self.spans = []

        # Check OCR need from extracted data (no additional PDF open)
        needs_ocr = False
        if not self.text.strip():
            needs_ocr = True
        else:
            from file_parser import is_text_garbled
            if is_text_garbled(self.text):
                needs_ocr = True
            elif self.spans:
                page_count = max(s.page_number for s in self.spans) + 1
                avg_chars = len(self.text.strip()) / max(page_count, 1)
                if avg_chars < 50:
                    needs_ocr = True

        if needs_ocr:
            from pdf_ocr import ocr_pdf
            logger.info("PDF needs OCR, falling back to OCR extraction")
            text = ocr_pdf(self.file_path)
            if text and text.strip():
                # Apply sanitization to OCR text too
                from file_parser import sanitize_control_chars, _clean_pdf_text
                text = _clean_pdf_text(text)
                self.text = text
            else:
                self.text = ""
            self.spans = []  # no spans available for OCR text

        return needs_ocr

    def _get_page_count(self) -> int:
        """Get the number of pages in the PDF."""
        from pdf_ocr import get_page_count
        return get_page_count(self.file_path)

    def _filter_spans(self, spans: list) -> list:
        """Keep only spans from pages < max_pages. Returns all if max_pages is 0."""
        if self.max_pages <= 0:
            return spans
        return [s for s in spans if s.page_number < self.max_pages]
