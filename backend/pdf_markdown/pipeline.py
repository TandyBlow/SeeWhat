"""
Full PDF-to-Markdown pipeline orchestrator.

Coordinates all stages: text extraction → formula extraction → segmentation →
metadata rules → LLM annotation → merge → review → final markdown.

Supports both synchronous (run) and streaming (run_streaming) modes.

Text/span alignment: the pipeline uses spans as the SINGLE SOURCE OF TRUTH
for text layout. Text is reconstructed via spans_to_text() so that all
position-based operations stay aligned. NEVER use parse_pdf() text with
span offsets.
"""

from __future__ import annotations

import logging

from .annotation_schema import SSEMessage, LabeledSpan
from .text_segmenter import segment_text
from .metadata_rules import apply_metadata_rules
from .formula_extractor import extract_formulas
from .llm_annotator import annotate_document
from .merge_engine import merge_annotations
from .review_layer import check_annotation_rules, llm_review_violations
from .pipeline_extraction_mixin import ExtractionMixin
from .pipeline_metadata_mixin import MetadataMixin
from .pipeline_fragment_mixin import FragmentMixin
from .pipeline_annotation_stage_mixin import AnnotationStageMixin
from .pipeline_streaming_mixin import StreamingMixin

logger = logging.getLogger(__name__)


class FullPipeline(ExtractionMixin, StreamingMixin, FragmentMixin, MetadataMixin, AnnotationStageMixin):
    """Orchestrates the complete PDF-to-Markdown pipeline."""

    def __init__(self, file_path: str, max_pages: int = 0):
        """Args:
            file_path: Path to the PDF file.
            max_pages: If >0, only process the first N pages (for fast testing).
        """
        self.file_path = file_path
        self.max_pages = max_pages
        self.text: str = ""
        self.spans: list = []
        self.formulas: list[LabeledSpan] = []
        self.metadata_markers: dict = {}
        self.segments: list = []
        self.llm_annotations: list = []
        self.markdown: str = ""
        self.violations: list = []

    def run(self) -> str:
        """Run the full pipeline synchronously. Returns final Markdown."""
        # Stage 1+2: Extract text and spans in a single pass, check OCR need
        needs_ocr = self._extract_and_check()

        if not self.text.strip():
            logger.warning("Empty text extracted from PDF")
            return ""

        # Stage 3: Formula extraction
        if not needs_ocr and self.spans:
            try:
                self.formulas = extract_formulas(self.file_path, self.spans)
                logger.info(f"Extracted {len(self.formulas)} formula regions")
            except Exception as e:
                logger.warning(f"Formula extraction failed (non-fatal): {e}")
                self.formulas = []

        # Stage 4: Metadata rules (bold/italic/mono)
        if self.spans:
            self.metadata_markers = apply_metadata_rules(self.spans)
            # Suppress italic markers in math-heavy documents
            self._suppress_formatting_if_math_heavy()

        # Stage 5: Segment text
        span_page_map = {}
        for span in self.spans:
            span_page_map[span.char_start] = span.page_number

        self.segments = segment_text(self.text, span_page_map)
        total_sentences = len(self.segments)
        logger.info(f"Segmented into {total_sentences} sentences")

        if total_sentences == 0:
            return self.text

        # Stage 6: LLM annotation
        try:
            self.llm_annotations = annotate_document(self.segments, self.text)
            logger.info(f"LLM annotation produced {len(self.llm_annotations)} sentence annotations")
        except Exception as e:
            logger.error(f"LLM annotation failed: {e}")
            return self.text

        # Stage 7: Merge
        self.markdown = merge_annotations(
            self.text,
            self.metadata_markers,
            self.llm_annotations,
            self.formulas,
        )

        # Stage 8: Review
        self.violations = check_annotation_rules(self.llm_annotations, self.text)
        if self.violations:
            errors = [v for v in self.violations if v.severity == "error"]
            warnings = [v for v in self.violations if v.severity == "warning"]
            logger.info(f"Review: {len(errors)} errors, {len(warnings)} warnings")

            if errors:
                self.llm_annotations = llm_review_violations(
                    self.violations,
                    self.text,
                    self.llm_annotations,
                )
                # Re-merge with corrected annotations
                self.markdown = merge_annotations(
                    self.text,
                    self.metadata_markers,
                    self.llm_annotations,
                    self.formulas,
                )

        return self.markdown
