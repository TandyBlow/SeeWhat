"""
Public process_chat_turn dispatcher: saves the user message, classifies intent,
runs tone/gap/enrichment preprocessing, then routes to the line-by-line handler
(via handler_router) or the single-topic handler.
"""
import logging
import time
from typing import Dict, Any

from session_store import load_session
from intent_classifier import classify_intent
from tone_wrapper import detect_tone
from knowledge_gap_detector import detect_gaps, format_gap_warning, should_check_gaps

from chat_enrichment import enrich_chat_context
from chat_line_by_line_turn import _process_line_by_line_turn
from chat_single_topic_turn import _process_single_topic_turn

logger = logging.getLogger(__name__)


def process_chat_turn(
    session_id: str,
    user_answer: str,
    skip: bool = False
) -> Dict[str, Any]:
    """Process one turn of a chat. Dispatches to single-topic, multi-KP, or line-by-line handler."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session["last_activity_at"] = time.time()

    # Save user message centrally — all sub-handlers read from session["messages"]
    session["messages"].append({
        "role": "user",
        "content": user_answer,
        "timestamp": time.time(),
    })

    # Classify user intent (rule-based primary, LLM fallback for ambiguous)
    if skip:
        intent = "skip_request"
    else:
        chat_mode = session.get("chat_mode", "single")
        intent = classify_intent(user_answer, chat_mode)

    # ── Preprocessing: run for ALL modes ──────────────────────────────
    chat_mode = session.get("chat_mode", "single")

    # Tone detection — all modes
    tone = detect_tone(session)

    # Knowledge gap detection — all modes
    gap_warning = ""
    if should_check_gaps(session):
        gap_result = detect_gaps(session["owner_id"], session["node_id"])
        gap_warning = format_gap_warning(gap_result)
        session["last_gap_check_turn"] = sum(1 for m in session["messages"] if m["role"] == "user")

    # Concept extraction + knowledge retrieval — all modes
    try:
        enrich_chat_context(session, intent)
    except Exception as e:
        logger.warning("enrich_chat_context failed for session %s: %s", session.get("session_id"), e)

    if chat_mode == "line_by_line":
        from handler_router import route_and_handle
        result = route_and_handle(session, user_answer, intent, tone, gap_warning)
        if result.get("_routed") is False:
            return _process_line_by_line_turn(session, user_answer, skip, intent)
        save_session(session)
        return result
    else:
        return _process_single_topic_turn(session, user_answer, skip, intent, tone, gap_warning)
