"""Layer 2 LLM review of rule-violating regions.

Re-annotates error-level violating regions via llm_annotator.annotate_chunk,
with paragraph fallback, then merges fixes back into the original annotation
list.
"""

from __future__ import annotations

import logging

from .annotation_schema import (
    StructuralLabel,
    LabeledSpan,
    SentenceAnnotation,
    RuleViolation,
)

from .review_rules import filter_error_violations

logger = logging.getLogger(__name__)


def llm_review_violations(
    violations: list[RuleViolation],
    text: str,
    original_annotations: list[SentenceAnnotation],
) -> list[SentenceAnnotation]:
    """Send rule-violating regions to LLM for re-annotation.

    Only reviews error-level violations. Warnings are logged but not re-annotated.
    Returns corrected annotations (merges fixes with original).
    """
    errors = filter_error_violations(violations)
    if not errors:
        logger.info("No error-level violations to review")
        return original_annotations

    # Build a set of affected sentence IDs
    affected_ids: set[int] = set()
    for violation in errors:
        v_start, v_end = violation.region
        for sent_ann in original_annotations:
            if sent_ann.char_start <= v_start < sent_ann.char_end or \
               sent_ann.char_start < v_end <= sent_ann.char_end:
                affected_ids.add(sent_ann.sentence_id)

    if not affected_ids:
        return original_annotations

    logger.info(f"LLM review: {len(errors)} violations affecting {len(affected_ids)} sentences")

    # Build segments for affected sentences with context
    from .text_segmenter import Segment
    affected_segments: list[Segment] = []
    for sent_ann in original_annotations:
        if sent_ann.sentence_id in affected_ids:
            # Include surrounding context (200 chars each side)
            ctx_before = text[max(0, sent_ann.char_start - 200):sent_ann.char_start]
            ctx_after = text[sent_ann.char_end:min(len(text), sent_ann.char_end + 200)]
            affected_segments.append(Segment(
                sentence_id=sent_ann.sentence_id,
                text=text[sent_ann.char_start:sent_ann.char_end],
                char_start=sent_ann.char_start,
                char_end=sent_ann.char_end,
                context_before=ctx_before,
                context_after=ctx_after,
            ))

    # Call LLM for re-annotation
    from .llm_annotator import annotate_chunk
    try:
        corrected_annotations = annotate_chunk(affected_segments, text)
    except RuntimeError as e:
        logger.warning(f"LLM review re-annotation failed: {e}")
        # Fall back to paragraph (previous stub behavior)
        corrected_annotations = [
            SentenceAnnotation(
                sentence_id=seg.sentence_id,
                char_start=seg.char_start,
                char_end=seg.char_end,
                labels=[LabeledSpan(
                    label=StructuralLabel.PARAGRAPH,
                    char_start=seg.char_start,
                    char_end=seg.char_end,
                    confidence=0.0,
                )],
            )
            for seg in affected_segments
        ]

    # Merge corrected annotations back into original list
    corrected_dict = {sa.sentence_id: sa for sa in corrected_annotations}
    result: list[SentenceAnnotation] = []
    for sent_ann in original_annotations:
        if sent_ann.sentence_id in corrected_dict:
            result.append(corrected_dict[sent_ann.sentence_id])
        else:
            result.append(sent_ann)

    return result
