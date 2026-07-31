"""
Public annotation orchestration for PDF text.

Sends sentence chunks to the LLM and builds validated SentenceAnnotation
objects, plus whole-document chunked annotation with cross-chunk merging.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, LabeledSpan, SentenceAnnotation
from .annotate_core import call_llm_with_retry, _parse_llm_json, logger
from .annotate_llm import (
    ANNOTATION_SYSTEM_PROMPT,
    _format_chunk_for_llm,
    _validate_annotation,
)


def annotate_chunk(
    segments,
    full_text: str,
) -> list[SentenceAnnotation]:
    """Send a chunk of segments to the LLM for structural annotation.

    Args:
        segments: List of Segment objects to annotate.
        full_text: The complete document text (for position validation).

    Returns:
        List of SentenceAnnotation objects with validated labels.
    """
    if not segments:
        return []

    formatted = _format_chunk_for_llm(segments)

    user_prompt = (
        "Annotate the following document text with structural labels.\n"
        "Each segment is shown with its absolute character position range and surrounding context.\n"
        "Label the TEXT content only, excluding bullet markers, number prefixes, and leading whitespace from label ranges.\n\n"
        + formatted
    )

    messages = [
        {"role": "system", "content": ANNOTATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw = call_llm_with_retry(messages)
    parsed = _parse_llm_json(raw)

    if parsed is None:
        logger.error(f"Failed to parse LLM JSON response: {raw[:500]}")
        # Fall back: all sentences are paragraphs
        return [
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
            for seg in segments
        ]

    annotations: list[SentenceAnnotation] = []
    raw_sentences = parsed.get("sentences", [])
    if not raw_sentences:
        raw_sentences = parsed.get("annotations", [])

    for raw_sent in raw_sentences:
        labels: list[LabeledSpan] = []
        for raw_label in raw_sent.get("labels", []):
            label_str = raw_label.get("label", "paragraph")
            try:
                label_type = StructuralLabel(label_str)
            except ValueError:
                logger.warning(f"Unknown label '{label_str}', defaulting to paragraph")
                label_type = StructuralLabel.PARAGRAPH

            labels.append(LabeledSpan(
                label=label_type,
                char_start=raw_label.get("char_start", 0),
                char_end=raw_label.get("char_end", 0),
                nesting_level=raw_label.get("nesting_level", 0),
                confidence=raw_label.get("confidence", 0.8),
            ))

        sent = SentenceAnnotation(
            sentence_id=raw_sent.get("sentence_id", 0),
            char_start=raw_sent.get("char_start", 0),
            char_end=raw_sent.get("char_end", 0),
            labels=labels,
        )
        sent = _validate_annotation(sent, full_text)
        annotations.append(sent)

    return annotations


def annotate_document(
    segments,
    full_text: str,
    chunk_size: int = 50,
    overlap: int = 3,
) -> list[SentenceAnnotation]:
    """Annotate a full document, splitting into chunks for the LLM.

    Handles cross-chunk coordination: for overlapping segments, prefers
    the annotation from the chunk where the segment is centered.
    """
    if not segments:
        return []

    from .text_segmenter import chunk_segments
    chunks = chunk_segments(segments, chunk_size=chunk_size, overlap=overlap)

    all_annotations: dict[int, list[SentenceAnnotation]] = {}

    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Annotating chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} sentences)")
        try:
            chunk_annotations = annotate_chunk(chunk, full_text)
            all_annotations[chunk_idx] = chunk_annotations
        except RuntimeError as e:
            logger.error(f"Chunk {chunk_idx} annotation failed: {e}")
            # Create paragraph-fallback annotations for this chunk
            all_annotations[chunk_idx] = [
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
                for seg in chunk
            ]

    # Merge: for overlapping sentences, prefer the chunk where the segment is centered
    # Track which chunk produced each annotation so we look up in the correct source chunk
    final: dict[int, SentenceAnnotation] = {}
    chunk_source: dict[int, int] = {}  # sentence_id → chunk_idx that produced the annotation

    for chunk_idx, annotations in all_annotations.items():
        chunk = chunks[chunk_idx]
        chunk_size_actual = len(chunk)
        for sent_ann in annotations:
            sent_id = sent_ann.sentence_id
            position_in_chunk = next(
                (i for i, s in enumerate(chunk) if s.sentence_id == sent_id),
                chunk_size_actual // 2,
            )
            distance_from_edge = min(position_in_chunk, chunk_size_actual - 1 - position_in_chunk)

            if sent_id not in final:
                final[sent_id] = sent_ann
                chunk_source[sent_id] = chunk_idx
            else:
                # Look up existing annotation in its SOURCE chunk (not always chunks[0])
                source_chunk_idx = chunk_source[sent_id]
                source_chunk = chunks[source_chunk_idx]
                source_chunk_size = len(source_chunk)
                existing_pos = next(
                    (i for i, s in enumerate(source_chunk) if s.sentence_id == sent_id),
                    source_chunk_size // 2,
                )
                existing_distance = min(existing_pos, source_chunk_size - 1 - existing_pos)
                if distance_from_edge > existing_distance:
                    final[sent_id] = sent_ann
                    chunk_source[sent_id] = chunk_idx

    return [final[sid] for sid in sorted(final.keys())]
