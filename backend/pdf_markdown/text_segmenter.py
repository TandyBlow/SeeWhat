"""
Split extracted text into sentences with context windows for LLM annotation.

Handles mixed Chinese/English text. Each segment carries surrounding context
so the LLM can make informed structural decisions per sentence.

IMPORTANT: this module must preserve \n characters from the original text
(spans-based text). Converting \n to space would break char_start/char_end
alignment and destroy the document's line structure. Paragraph breaks are
\n\n (from spans_to_text), not heuristic-detected.

Split shim: names re-exported from segment_models / segment_split / segment_text.
"""

from .segment_models import Segment
from .segment_split import _LATIN_SPLIT_MIN_LEN, _LIST_MARKER_RE, _split_into_raw_sentences
from .segment_text import _MIN_MERGE_LEN, chunk_segments, get_sentence_count, segment_text, text_from_segments
