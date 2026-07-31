"""
Document position tracker for line-by-line chat mode.
Code tracks which sentence we're on — the AI no longer needs to
"find its position" by reading conversation history.

Split into doc_split (text segmentation) and doc_position (session position).
"""
from doc_split import split_document
from doc_position import (
    get_current_segment,
    advance_position,
    get_progress_context,
    is_document_done,
    get_full_document,
    get_position_marker,
    get_context_window,
)
