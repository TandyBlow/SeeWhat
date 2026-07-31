"""
Primary line-by-line mode handlers: explain (confirmation/skip), answer
(content/knowledge questions), end, and the fallback that delegates to explain.
Handlers carry @_register decorators that populate handler_core._ROUTE_TABLE
at import time.
"""
import time

from handler_prompts import (
    build_line_by_line_explain_prompt,
    build_line_by_line_answer_prompt,
)
from doc_position_tracker import (
    get_current_segment,
    advance_position,
    get_progress_context,
    is_document_done,
    get_context_window,
    get_position_marker,
)
from chat_service import (
    call_deepseek,
    parse_json_response,
)
from handler_core import (
    _register,
    _recent_history,
    _end_line_by_line_result,
    _extract_mentioned_concepts,
)
from handler_sanitize import _sanitize_line_by_line_response


@_register("line_by_line", "confirmation")
@_register("line_by_line", "skip_request")
def handle_line_by_line_explain(session: dict, user_input: str, intent: str,
                                 tone: dict, gap_warning: str) -> dict:
    """User said 'continue' or 'skip' — advance and explain next segment."""
    if is_document_done(session):
        return _end_line_by_line_result(session, "文档已经讲解完毕。")

    # Confirmation means "I understood the previous segment, move forward"
    # Advance FIRST, then explain the new current segment
    advance_position(session)
    if is_document_done(session):
        return _end_line_by_line_result(session, "文档已经讲解完毕。")

    current_segment = get_current_segment(session)
    progress = get_progress_context(session)
    ctx_window = get_context_window(session)
    pos_marker = get_position_marker(session)

    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")

    # Read enriched context from pre-processing pipeline
    # (concept extraction + knowledge retrieval by content — already filtered by relevance)
    enriched = session.get("_enriched_context", {}) or {}
    concept_ctx = enriched.get("concept_context", "")
    personalized = enriched.get("personalized_context", "")
    expansion = enriched.get("expansion_context", "")
    import sys
    print(f"[HANDLER explain] concept_ctx={len(concept_ctx)}chars, personalized={len(personalized)}chars, expansion={len(expansion)}chars", file=sys.stderr)

    recent = _recent_history(session, 6)
    messages = build_line_by_line_explain_prompt(
        current_segment=current_segment,
        progress=progress,
        knowledge_profile="",  # enriched context replaces full profile
        gap_warning=gap_warning,
        tone_instruction=tone.get("instruction", ""),
        recent_history=recent,
        context_window=ctx_window,
        position_marker=pos_marker,
        concept_context=concept_ctx,
        personalized_context=personalized,
        expansion_context=expansion,
    )

    raw = call_deepseek(messages)
    result = parse_json_response(raw)

    ai_message = _sanitize_line_by_line_response(
        result.get("message", ""), current_segment)
    action = result.get("action", "explain")

    # Position already advanced at start — just check if done
    if is_document_done(session):
        action = "end_explanation"

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "reason": result.get("reason", "")},
    })

    return {
        "action": action,
        "ai_message": ai_message,
        "sub_topic": result.get("reason", ""),
        "generated_content": "",
        "knowledge_note": "",
        "completed": action == "end_explanation",
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }


@_register("line_by_line", "content_question")
@_register("line_by_line", "knowledge_question")
def handle_line_by_line_answer(session: dict, user_input: str, intent: str,
                                tone: dict, gap_warning: str) -> dict:
    """User asked a content question — answer briefly then continue."""
    if is_document_done(session):
        return _end_line_by_line_result(session, "文档已经讲解完毕。")

    current_segment = get_current_segment(session)
    progress = get_progress_context(session)
    ctx_window = get_context_window(session)
    pos_marker = get_position_marker(session)

    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")

    # Read enriched context from pre-processing pipeline
    enriched = session.get("_enriched_context", {}) or {}
    concept_ctx = enriched.get("concept_context", "")
    personalized = enriched.get("personalized_context", "")
    expansion = enriched.get("expansion_context", "")
    def_chain = enriched.get("definition_chain", "")

    recent = _recent_history(session, 6)
    messages = build_line_by_line_answer_prompt(
        current_segment=current_segment,
        progress=progress,
        user_question=user_input,
        knowledge_profile="",  # enriched context replaces full profile
        gap_warning=gap_warning,
        tone_instruction=tone.get("instruction", ""),
        recent_history=recent,
        context_window=ctx_window,
        position_marker=pos_marker,
        concept_context=concept_ctx,
        personalized_context=personalized,
        expansion_context=expansion,
        definition_chain=def_chain,
    )

    raw = call_deepseek(messages)
    result = parse_json_response(raw)

    ai_message = _sanitize_line_by_line_response(
        result.get("message", ""), current_segment)
    action = result.get("action", "explain")

    # Do NOT advance — user asked a question, stay on current segment
    if is_document_done(session):
        action = "end_explanation"

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "reason": result.get("reason", "")},
    })

    return {
        "action": action,
        "ai_message": ai_message,
        "sub_topic": result.get("reason", ""),
        "generated_content": "",
        "knowledge_note": "",
        "completed": action == "end_explanation",
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }


@_register("line_by_line", "end_request")
def handle_line_by_line_end(session: dict, user_input: str, intent: str,
                             tone: dict, gap_warning: str) -> dict:
    """User wants to end the line-by-line session."""
    return _end_line_by_line_result(session, "好的，讲解到这里。你可以随时回来继续。")


# ── Fallback Handler ──────────────────────────────────────────────────

def handle_line_by_line_fallback(session: dict, user_input: str, intent: str,
                                  tone: dict, gap_warning: str) -> dict:
    """Fallback: treat as confirmation and explain next segment."""
    return handle_line_by_line_explain(session, user_input, "confirmation", tone, gap_warning)
