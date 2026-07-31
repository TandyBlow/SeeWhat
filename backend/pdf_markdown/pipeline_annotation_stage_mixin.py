"""
Annotation and review stage mixin: streaming LLM annotation with
deduplication, plus the rule-review and completion stage.

Part of the FullPipeline split. Called via self by run_streaming().
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

from .annotation_schema import SentenceAnnotation, SSEMessage
from .llm_annotator import annotate_chunk
from .merge_engine import merge_annotations
from .review_layer import check_annotation_rules, llm_review_violations
from .streaming import (
    annotation_progress,
    pipeline_error,
    review_issue,
    pipeline_complete,
)

logger = logging.getLogger(__name__)


class AnnotationStageMixin:
    """Streaming LLM annotation and review stages of the PDF pipeline."""

    async def _stream_annotation_stage(
        self, _progress, total_sentences: int
    ) -> AsyncGenerator[SSEMessage, None]:
        """Stream LLM annotation of segments in chunks with deduplication.

        Mirrors the original early-return error path via the
        self._annotation_failed flag.
        """
        from .text_segmenter import chunk_segments
        from .llm_annotator import annotate_chunk

        chunks = chunk_segments(self.segments, chunk_size=20, overlap=2)
        # Use dict-based dedup instead of extend — prevents 7x repetition
        annotation_dict: dict[int, SentenceAnnotation] = {}
        total_chunks = len(chunks)

        yield _progress("annotate", f"Annotating structure with LLM ({total_chunks} chunks)...", 35)

        for chunk_idx, chunk in enumerate(chunks):
            yield annotation_progress(
                sum(len(c) for c in chunks[:chunk_idx]),
                total_sentences,
            )
            yield _progress(
                "annotate",
                f"LLM chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} sentences)...",
                35 + int((chunk_idx / max(total_chunks, 1)) * 40),
            )

            try:
                chunk_annotations = await asyncio.to_thread(
                    annotate_chunk, chunk, self.text
                )
            except Exception as e:
                logger.error(f"Chunk {chunk_idx} annotation failed: {e}")
                self._annotation_failed = True
                yield pipeline_error(
                    "annotation",
                    f"LLM annotation failed for chunk {chunk_idx + 1}/{total_chunks}: {e}",
                    recoverable=False,
                )
                return

            # Log label distribution for debugging
            label_counts: dict[str, int] = {}
            for sa in chunk_annotations:
                for ls in sa.labels:
                    label_counts[ls.label.value] = label_counts.get(ls.label.value, 0) + 1
            logger.info(f"Chunk {chunk_idx} LLM labels: {label_counts}")

            # Deduplicate: keep annotation with highest avg confidence per sentence_id
            for sent_ann in chunk_annotations:
                sid = sent_ann.sentence_id
                if sid not in annotation_dict:
                    annotation_dict[sid] = sent_ann
                else:
                    new_avg = sum(l.confidence for l in sent_ann.labels) / max(len(sent_ann.labels), 1)
                    existing_avg = sum(l.confidence for l in annotation_dict[sid].labels) / max(len(annotation_dict[sid].labels), 1)
                    if new_avg > existing_avg:
                        annotation_dict[sid] = sent_ann

            yield _progress(
                "annotate", f"Chunk {chunk_idx + 1}/{total_chunks} done",
                35 + int(((chunk_idx + 1) / max(total_chunks, 1)) * 40),
            )

            # Yield per-sentence fragments for SSE streaming
            for sent_ann in chunk_annotations:
                yield self._build_sentence_result(sent_ann)

            yield annotation_progress(
                sum(len(c) for c in chunks[:chunk_idx + 1]),
                total_sentences,
            )

        # Convert deduplicated dict to sorted list
        self.llm_annotations = [
            annotation_dict[sid] for sid in sorted(annotation_dict.keys())
        ]

    async def _stream_review_stage(
        self, _progress
    ) -> AsyncGenerator[SSEMessage, None]:
        """Stream the review stage: violations, auto-fixes, and completion."""
        # Stage 8: Review
        yield _progress("review", "Checking annotation rules...", 93)
        self.violations = check_annotation_rules(self.llm_annotations, self.text)
        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]

        for v in self.violations:
            yield review_issue(v.region, v.rule_name, "detected")

        if errors:
            self.llm_annotations = await asyncio.to_thread(
                llm_review_violations,
                self.violations, self.text, self.llm_annotations
            )
            self.markdown = merge_annotations(
                self.text, self.metadata_markers,
                self.llm_annotations, self.formulas,
            )
            for v in errors:
                yield review_issue(v.region, v.rule_name, "auto_fixed")

        unresolved = len(errors)
        yield pipeline_complete(
            total_markdown_length=len(self.markdown),
            issues_found=len(self.violations),
            issues_resolved=len(errors),
            unresolved=unresolved,
            final_markdown=self.markdown,
        )
