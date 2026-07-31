"""
Routing table and dispatcher for the refactored chat architecture.
Maps (chat_mode, intent) pairs to narrow handler functions.
Base module in the handler dependency graph — must not import from any
sibling module at module level.
"""
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)


# ── Routing Table ─────────────────────────────────────────────────────

# Maps (chat_mode, intent) → handler_function
_ROUTE_TABLE: Dict[tuple, callable] = {}


def _register(chat_mode: str, intent: str):
    """Decorator to register a handler in the routing table."""
    def decorator(fn):
        _ROUTE_TABLE[(chat_mode, intent)] = fn
        return fn
    return decorator


# ── Public API ────────────────────────────────────────────────────────

def route_and_handle(
    session: dict,
    user_input: str,
    intent: str,
    tone: dict,
    gap_warning: str,
) -> dict:
    """Route to the correct handler based on chat_mode + intent, execute, return result."""
    chat_mode = session.get("chat_mode", "single")
    key = (chat_mode, intent)

    handler = _ROUTE_TABLE.get(key)
    if handler is None and chat_mode == "line_by_line":
        from handler_line_by_line import handle_line_by_line_fallback
        handler = handle_line_by_line_fallback

    if handler:
        return handler(session, user_input, intent, tone, gap_warning)

    # For non-line-by-line modes, return a sentinel that tells process_chat_turn
    # to use the existing legacy handling
    return {"_routed": False, "intent": intent}


# ── Helpers ───────────────────────────────────────────────────────────

def _recent_history(session: dict, n: int = 6) -> str:
    """Get the last N messages as a formatted string."""
    msgs = session.get("messages", [])
    recent = msgs[-n:] if len(msgs) > n else msgs
    lines = []
    for msg in recent:
        role_label = "AI" if msg["role"] == "ai" else "用户"
        content = msg["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)


def _end_line_by_line_result(session: dict, message: str) -> dict:
    """Build a standardized 'end explanation' result."""
    session["status"] = "completed"
    session["messages"].append({
        "role": "ai",
        "content": message,
        "timestamp": time.time(),
        "metadata": {"action": "end_explanation"},
    })
    return {
        "action": "end_explanation",
        "ai_message": message,
        "sub_topic": "",
        "generated_content": "",
        "knowledge_note": "",
        "completed": True,
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }


def _extract_mentioned_concepts(session: dict) -> list:
    """Extract mentioned concepts from the session's enriched context, excluding
    concepts that already exist as children of the current node.

    Lazily triggers post-response concept extraction from the AI's latest reply,
    so the chips reflect what was actually taught rather than broad conversation topics.
    """
    # Trigger post-response extraction if not yet done this turn
    if not session.get("_response_concepts") and not session.get("_response_extraction_attempted"):
        session["_response_extraction_attempted"] = True
        try:
            from chat_service import _refresh_response_concepts
            _refresh_response_concepts(session)
        except Exception as e:
            logger.warning("_refresh_response_concepts failed in handler_router: %s", e)
            pass

    enriched = session.get("_enriched_context", {}) or {}
    # Prefer post-response concepts (extracted from AI's actual reply) over
    # pre-processing concepts (extracted from conversation history before AI responded)
    raw_concepts = session.get("_response_concepts") or enriched.get("concepts", [])
    if not raw_concepts:
        return []

    # Fetch existing child names so we can skip concepts the user already has
    existing_names: set = set()
    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")
    if oid and nid:
        try:
            from tree_repository_sqlite import get_db_ctx as _get_db_ctx
            with _get_db_ctx() as _conn:
                rows = _conn.execute(
                    "SELECT name FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
                    (oid, nid)
                ).fetchall()
                existing_names = {r["name"] for r in rows}
        except Exception as e:
            logger.warning("Failed to fetch existing names for dedup in handler_router: %s", e)

    result = []
    for c in raw_concepts:
        name = c.get("name", "")
        if name in existing_names:
            continue
        result.append({
            "name": name,
            "category": c.get("category", ""),
            "definition": c.get("definition", ""),
            "prerequisites": c.get("prerequisites", []),
            "expansion_directions": c.get("expansion_directions", []),
            "verified": c.get("verified", False),
            "wiki_summary": c.get("wiki_summary", ""),
            "wiki_description": c.get("wiki_description", ""),
        })
    return result
