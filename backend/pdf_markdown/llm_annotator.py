"""
LLM-based structural annotation for PDF text.

Sends sentence chunks to the LLM for structural labeling. The LLM outputs
character-position labels; it never generates or modifies text content.

Re-export shim — implementations live in annotate_core, annotate_llm, and
annotate_runner.
"""

from .annotate_core import (
    BASE_DELAY,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT,
    MAX_RETRIES,
    _parse_llm_json,
    call_llm_with_retry,
    logger,
)
from .annotate_llm import (
    ANNOTATION_SYSTEM_PROMPT,
    _format_chunk_for_llm,
    _validate_annotation,
)
from .annotate_runner import (
    annotate_chunk,
    annotate_document,
)
