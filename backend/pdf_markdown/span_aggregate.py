"""
Post-extraction span aggregation.

Merges consecutive same-format spans into SpanGroups without crossing page
boundaries, reconstructs plain text that round-trips with the offset model,
and detects the body font size via mode of sizes.
"""

from __future__ import annotations

from .span_models import Span, SpanGroup


def group_spans(spans: list[Span]) -> list[SpanGroup]:
    """Merge consecutive spans with identical bold/italic/monospace state.

    Does NOT merge across page boundaries — spans from different pages have
    different spatial positions and should never be grouped together.
    """
    if not spans:
        return []

    groups: list[SpanGroup] = []
    cur_spans: list[Span] = [spans[0]]
    cur_state = (spans[0].is_bold, spans[0].is_italic, spans[0].is_monospace)

    for span in spans[1:]:
        state = (span.is_bold, span.is_italic, span.is_monospace)
        same_page = span.page_number == cur_spans[-1].page_number

        if state == cur_state and same_page:
            cur_spans.append(span)
        else:
            text = "".join(s.text for s in cur_spans)
            groups.append(SpanGroup(
                spans=cur_spans,
                is_bold=cur_state[0],
                is_italic=cur_state[1],
                is_monospace=cur_state[2],
                text=text,
                char_start=cur_spans[0].char_start,
                char_end=cur_spans[-1].char_end,
            ))
            cur_spans = [span]
            cur_state = state

    if cur_spans:
        text = "".join(s.text for s in cur_spans)
        groups.append(SpanGroup(
            spans=cur_spans,
            is_bold=cur_state[0],
            is_italic=cur_state[1],
            is_monospace=cur_state[2],
            text=text,
            char_start=cur_spans[0].char_start,
            char_end=cur_spans[-1].char_end,
        ))

    return groups


def spans_to_text(spans: list[Span]) -> str:
    """Reconstruct plain text from extracted spans, including all separators.

    The reconstructed text EXACTLY matches the offset model used by
    extract_spans(): span.char_start and span.char_end positions are valid
    indices into this text, and text[span.char_start:span.char_end] == span.text.
    """
    if not spans:
        return ""
    parts: list[str] = []
    for span in spans:
        parts.append(span.text)
        parts.append(span.separator_after)
    return "".join(parts)


def detect_body_size(spans: list[Span]) -> float:
    """Detect the body text font size (mode of all sizes)."""
    from collections import Counter

    sizes = [s.font_size for s in spans if s.font_size > 0]
    if not sizes:
        return 12.0

    size_counts = Counter(sizes)
    min_count = max(len(sizes) * 0.005, 2)
    common_sizes = {s for s, c in size_counts.items() if c >= min_count}
    if common_sizes:
        return max(common_sizes, key=lambda s: size_counts[s])
    return size_counts.most_common(1)[0][0]
