"""
Split extracted text into sentences with context windows for LLM annotation.

Handles mixed Chinese/English text. Each segment carries surrounding context
so the LLM can make informed structural decisions per sentence.

IMPORTANT: this module must preserve \n characters from the original text
(spans-based text). Converting \n to space would break char_start/char_end
alignment and destroy the document's line structure. Paragraph breaks are
\n\n (from spans_to_text), not heuristic-detected.
"""

from __future__ import annotations

from .segment_models import Segment
from .segment_split import _LIST_MARKER_RE, _split_into_raw_sentences

_MIN_MERGE_LEN = 40  # minimum chars for a standalone sentence


def segment_text(
    text: str,
    span_page_map: dict[int, int] | None = None,
    context_size: int = 2,
) -> list[Segment]:
    """Split document text into sentences with context windows.

    Args:
        text: Full document plain text (from spans_to_text, with \n/\n\n preserved).
        span_page_map: Optional map from char_position to page_number.
        context_size: Number of surrounding sentences on each side.

    Returns:
        List of Segment objects ready for LLM annotation.
    """
    if span_page_map is None:
        span_page_map = {}

    raw = _split_into_raw_sentences(text)

    # Merge very short fragments with their neighbors
    merged: list[tuple[str, int, int]] = []
    for s_text, s_start, s_end in raw:
        stripped = s_text.strip()
        if not stripped:
            continue
        if merged and len(stripped) < _MIN_MERGE_LEN and not stripped[-1] in '.!?。！？' and not _LIST_MARKER_RE.match(stripped):
            # Merge into previous
            prev_text, prev_start, _ = merged[-1]
            merged[-1] = (prev_text + s_text, prev_start, s_end)
        else:
            merged.append((s_text, s_start, s_end))

    segments: list[Segment] = []
    for idx, (s_text, s_start, s_end) in enumerate(merged):
        # Build context
        before_start = max(0, idx - context_size)
        before = "".join(m[0] for m in merged[before_start:idx])

        after_end = min(len(merged), idx + context_size + 1)
        after = "".join(m[0] for m in merged[idx + 1:after_end])

        # Estimate page number from position map
        page = 0
        for pos in sorted(span_page_map.keys()):
            if pos <= s_start:
                page = span_page_map[pos]
            else:
                break

        segments.append(Segment(
            sentence_id=idx,
            text=s_text,
            char_start=s_start,
            char_end=s_end,
            context_before=before,
            context_after=after,
            page_number=page,
        ))

    return segments


def chunk_segments(
    segments: list[Segment],
    chunk_size: int = 50,
    overlap: int = 3,
) -> list[list[Segment]]:
    """Group segments into overlapping chunks for LLM processing.

    Args:
        segments: All segments in document order.
        chunk_size: Max segments per chunk.
        overlap: Number of overlapping segments between adjacent chunks.

    Returns:
        List of chunk segment groups.
    """
    if len(segments) <= chunk_size:
        return [segments]

    chunks: list[list[Segment]] = []
    start = 0
    while start < len(segments):
        end = min(start + chunk_size, len(segments))
        chunks.append(segments[start:end])
        if end >= len(segments):
            break
        start = end - overlap

    return chunks


def get_sentence_count(text: str) -> int:
    """Quick estimate of sentence count without full segmentation."""
    raw = _split_into_raw_sentences(text)
    return len([r for r in raw if r[0].strip()])


def text_from_segments(segments: list[Segment]) -> str:
    """Reconstruct full text from segments."""
    if not segments:
        return ""
    sorted_segs = sorted(segments, key=lambda s: s.char_start)
    return "".join(s.text for s in sorted_segs)
