"""
Extract spans from PDF with exact character positions and font metadata.

Walks PyMuPDF's get_text("dict") output, flattening blocks→lines→spans
while accumulating global character offsets. Bboxes are kept in page-local
coordinate space (PDF points) for spatial alignment with formula extraction.

This module is the SINGLE SOURCE OF TRUTH for the text layout. All downstream
position-based operations (formula extraction, metadata markers, merge engine,
LLM annotation) use offsets computed here. Text must be reconstructed via
spans_to_text() to maintain alignment — NEVER use parse_pdf() text with these
offsets.

Split shim: names re-exported from span_models / span_extract / span_aggregate.
"""

from .span_aggregate import detect_body_size, group_spans, spans_to_text
from .span_extract import MONO_KEYWORDS, _calc_span_flags, _is_mono_font, extract_spans
from .span_models import Span, SpanGroup
