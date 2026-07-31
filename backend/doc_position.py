"""
Session-position helpers for line-by-line chat mode.
Read the current segment, advance position, build progress indicators and
the context window. All operate purely on the caller-owned session dict;
no module-level state.
"""


def get_current_segment(session: dict) -> str:
    """Get the current document segment based on code-tracked position."""
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0)
    if pos < len(segments):
        return segments[pos]
    return ""


def advance_position(session: dict) -> bool:
    """Advance to the next segment. Returns True if more segments remain."""
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0) + 1
    session["current_position"] = pos
    return pos < len(segments)


def get_progress_context(session: dict) -> str:
    """Build a progress indicator string, e.g. '第 3/15 句'."""
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0)
    total = len(segments)
    if total == 0:
        return ""
    current_num = min(pos + 1, total)
    return f"第 {current_num}/{total} 句"


def is_document_done(session: dict) -> bool:
    """Check if all segments have been covered."""
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0)
    return pos >= len(segments)


def get_full_document(session: dict) -> str:
    """Return the full original document text stored in the session."""
    return session.get("full_document", "")


def get_position_marker(session: dict) -> str:
    """Build a position marker showing current location in the full document.

    Returns a string like '第 3/15 段' that marks where the AI is in the document.
    """
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0)
    total = len(segments)
    if total == 0:
        return ""
    return f"第 {min(pos + 1, total)}/{total} 段"


def get_context_window(session: dict, window_size: int = 3, future_preview_chars: int = 80) -> str:
    """Return a window of segments around the current position.

    Instead of dumping the entire document into every prompt (which dilutes
    attention), give the AI just enough surrounding context to understand
    where it is. When the user asks about something outside the window,
    code searches the full document separately.

    Future segments (not yet explained) are truncated to a short preview
    so the AI has directional awareness without enough detail to spoil.

    Args:
        session: Chat session dict with doc_segments and current_position.
        window_size: Number of segments before and after current position.
        future_preview_chars: Max chars to show for segments after current pos.

    Returns:
        Formatted string showing the context window with current position marked.
    """
    segments = session.get("doc_segments", [])
    pos = session.get("current_position", 0)
    total = len(segments)
    if total == 0:
        return ""

    start = max(0, pos - window_size)
    end = min(total, pos + window_size + 1)

    lines = []
    if start > 0:
        lines.append(f"...（前面还有 {start} 段，已讲解过）")
    for i in range(start, end):
        marker = "  ← 当前要讲解的" if i == pos else ""
        text = segments[i]
        if i > pos:
            text = text[:future_preview_chars] + ("..." if len(segments[i]) > future_preview_chars else "")
        lines.append(f"段{i + 1}/{total}{marker}:\n{text}")
    if end < total:
        lines.append(f"...（后面还有 {total - end} 段，尚未讲到）")

    return "\n\n".join(lines)
