"""
Background file-parse task manager with progress tracking.
Uses in-memory state dict + threading for single-server deployments.

After upload saves the file to disk, parsing runs on a daemon thread.
Frontend polls GET /upload-status/{file_id} for progress.

Stages: saving -> parsing -> ocr_check -> ready (or failed)

After parsing completes, a separate formatting thread converts the raw text
into clean Markdown with LaTeX math, caching it as {file_id}.formatted.txt.
This runs async so the file is "ready" immediately; formatting arrives a few
seconds later. Line-by-line chat picks up the formatted text automatically.
"""

from parse_format import format_document_text, should_preserve_verbatim
from parse_threads import enqueue_parse, get_parse_progress
