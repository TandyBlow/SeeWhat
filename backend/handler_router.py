"""
Handler router for the refactored chat architecture.
Maps (chat_mode, intent) pairs to narrow handler functions.
Shim module: re-exports every public name from the split handler modules so
existing import sites (chat_service and others) keep working unchanged.
"""
from handler_core import (
    _ROUTE_TABLE,
    _register,
    route_and_handle,
    _recent_history,
    _end_line_by_line_result,
    _extract_mentioned_concepts,
)
from handler_line_by_line import (
    handle_line_by_line_explain,
    handle_line_by_line_answer,
    handle_line_by_line_end,
    handle_line_by_line_fallback,
)
from handler_brief_reply import handle_line_by_line_brief_reply
from handler_sanitize import (
    _sanitize_line_by_line_response,
    _FORWARD_REF_RE,
    _MD_LINK_RE,
    _BLOCKQUOTE_LINE_RE,
    _SENTENCE_END_RE,
)
