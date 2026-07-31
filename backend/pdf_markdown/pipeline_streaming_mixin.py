"""
Streaming orchestration mixin: async SSE run_streaming for FullPipeline.

Keeps the extract/formula/metadata/segment stages and the merge stage
inline, delegates the annotation and review stages to AnnotationStageMixin.
The _progress nonlocal closure drives all stage timing.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncGenerator

from .annotation_schema import SSEMessage
from .streaming import pipeline_start, formula_progress, pipeline_error, pipeline_complete
from .formula_extractor import extract_formulas
from .metadata_rules import apply_metadata_rules
from .text_segmenter import segment_text
from .merge_engine import merge_annotations


class StreamingMixin:
    """SSE streaming orchestration stage of the PDF pipeline."""

    async def run_streaming(self) -> AsyncGenerator[SSEMessage, None]:
        """Run the pipeline with SSE streaming for each stage and sentence."""
        from .streaming import stage_progress

        t_start = time.time()
        t_stage_start = t_start
        t_prev_stage = 0.0

        def _progress(stage: str, detail: str = "", percent: int = 0) -> SSEMessage:
            nonlocal t_stage_start, t_prev_stage
            now = time.time()
            stage_ms = int((now - t_stage_start) * 1000)
            total_ms = int((now - t_start) * 1000)
            t_stage_start = now
            return stage_progress(stage, detail, percent, stage_ms, total_ms)

        file_name = os.path.basename(self.file_path)

        # Stage 1+2: Extract text and spans, check OCR
        yield _progress("extract", "Extracting text and spans from PDF...", 5)
        needs_ocr = await asyncio.to_thread(self._extract_and_check)

        if not self.text.strip():
            yield pipeline_error("extract", "Empty text extracted from PDF", False)
            return

        if needs_ocr:
            yield _progress("ocr", "OCR text extraction used", 10)
        else:
            yield _progress("spans", f"Extracted {len(self.spans)} spans", 10)

        # Emit pipeline_start with actual stats
        full_page_count = self._get_page_count()
        actual_pages = max(s.page_number for s in self.spans) + 1 if self.spans else full_page_count
        yield pipeline_start(file_name, actual_pages, len(self.text))

        # Stage 3: Formula extraction
        if not needs_ocr and self.spans:
            yield _progress("formula", "Detecting math regions...", 20)
            try:
                self.formulas = extract_formulas(self.file_path, self.spans)
                review_needed_count = sum(1 for f in self.formulas if f.confidence < 0.7)
                yield formula_progress(len(self.formulas), review_needed_count)
                yield _progress("formula", f"Found {len(self.formulas)} math regions", 25)
            except Exception as e:
                yield pipeline_error("formula", str(e), recoverable=True)
                self.formulas = []
        else:
            yield _progress("formula", "Skipping formula extraction (OCR path)", 25)

        # Stage 4: Metadata rules
        yield _progress("metadata", "Applying font metadata rules...", 28)
        if self.spans:
            self.metadata_markers = apply_metadata_rules(self.spans)
            # Suppress italic markers in math-heavy documents
            self._suppress_formatting_if_math_heavy()

        # Stage 5: Segmentation
        yield _progress("segment", "Splitting text into sentences...", 30)
        span_page_map = {}
        for span in self.spans:
            span_page_map[span.char_start] = span.page_number

        self.segments = segment_text(self.text, span_page_map)
        total_sentences = len(self.segments)

        if total_sentences == 0:
            yield pipeline_complete(0, 0, 0, 0)
            return

        yield _progress("segment", f"Split into {total_sentences} sentences", 32)

        # Stage 6: LLM annotation with deduplication (streamed per chunk)
        async for msg in self._stream_annotation_stage(_progress, total_sentences):
            yield msg
        if getattr(self, "_annotation_failed", False):
            return

        # Stage 7: Full merge
        yield _progress("merge", "Merging annotations into Markdown...", 88)
        self.markdown = merge_annotations(
            self.text,
            self.metadata_markers,
            self.llm_annotations,
            self.formulas,
        )

        # Stage 8: Review
        async for msg in self._stream_review_stage(_progress):
            yield msg
