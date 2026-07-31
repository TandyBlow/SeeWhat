"""
Line-by-line chat startup: reads uploaded/formatted file, pre-splits the
document, builds the first-segment prompt, and makes the initial DeepSeek call.
"""
import logging
import os
import time
from typing import Dict, Any

from doc_position_tracker import split_document, get_current_segment, get_progress_context, get_position_marker, get_context_window
from session_store import save_session

from chat_llm import call_deepseek, parse_json_response, _filter_meta_commentary
from chat_prompts import LINE_BY_LINE_SYSTEM
from chat_session import _read_uploaded_file, _get_node_name

logger = logging.getLogger(__name__)


def _start_line_by_line(
    session_id: str,
    node_id: str,
    owner_id: str,
    file_id: str,
    previous_node_id: str | None = None,
    transition_type: str = "initial",
    transition_reason: str = "",
    adaptive_opening: str = ""
) -> Dict[str, Any]:
    """Start a line-by-line explanation chat for a file, with context chain awareness."""
    full_text = _read_uploaded_file(owner_id, file_id) or ""

    # Prefer formatted text (from /format-content) if available — it's cleaner
    # markdown with proper LaTeX, which produces better-looking quotes in chat.
    fmt_cache = os.path.join(f"/tmp/acacia_uploads/{owner_id}", f"{file_id}.formatted.txt")
    if os.path.exists(fmt_cache):
        try:
            with open(fmt_cache, 'r', encoding='utf-8') as f:
                formatted = f.read()
            if formatted.strip():
                full_text = formatted
        except Exception as e:
            logger.warning("Failed to read formatted cache for %s: %s", file_id, e)

    node_name = _get_node_name(node_id)

    # Pre-split document into segments for code-tracked position
    doc_segments = split_document(full_text)

    from context_chain_service import build_transition_context_text

    transition_ctx = build_transition_context_text(
        owner_id, node_id, previous_node_id, transition_type, transition_reason
    ) if previous_node_id or transition_type != "initial" else ""

    session = {
        "session_id": session_id,
        "node_id": node_id,
        "owner_id": owner_id,
        "file_id": file_id,
        "knowledge_points": [{"id": "file", "title": node_name or "文件讲解", "type": "concept", "source_content": full_text}],
        "current_index": 0,
        "messages": [],
        "generated_content": "",
        "status": "active",
        "created_at": time.time(),
        "last_activity_at": time.time(),
        "follow_up_count": 0,
        "self_correction_count": 0,
        "uncertainty_count": 0,
        "pending_example": None,
        "example_history": [],
        "chat_mode": "line_by_line",
        "opening_message": adaptive_opening,
        "transition_context": transition_ctx,
        "previous_node_id": previous_node_id,
        "transition_reason": transition_reason,
        "doc_segments": doc_segments,
        "current_position": 0,
        "full_document": full_text,
    }

    # Build narrow prompt: the AI only needs to explain the first segment.
    # Code tracks position — AI never needs to find it.
    first_segment = get_current_segment(session)
    progress = get_progress_context(session)
    pos_marker = get_position_marker(session)

    user_lines = []
    # Context window — nearby segments for orientation, not the entire file
    ctx_window = get_context_window(session)
    if ctx_window:
        user_lines.append(f"【文档上下文】（当前位置附近的段落）\n{ctx_window}")
    if pos_marker:
        user_lines.append(f"【{pos_marker}】")
    user_lines.append(f"【逐句讲解】{progress}")
    user_lines.append(f"请解释下面这句话：\n\n{first_segment}")

    # Extract atomic concepts for the first segment (same as enrichment pipeline)
    # This replaces the full knowledge profile — concept extraction + knowledge retrieval
    # provides filtered, relevant context instead of dumping the entire user tree.
    try:
        from concept_extractor import extract_atomic_concepts, format_concept_context
        from knowledge_retriever import build_content_index, search_user_knowledge, format_personalized_context

        result = extract_atomic_concepts(first_segment, full_text)
        concepts = result.get("concepts", [])
        connections = result.get("cross_connections", [])
        if concepts:
            cc = format_concept_context(concepts, connections)
            if cc:
                user_lines.append(cc)
            # Also search user knowledge by content for personalized context
            try:
                index = build_content_index(owner_id)
                matches = search_user_knowledge(concepts, index)
                personalized = format_personalized_context(matches)
                if personalized:
                    user_lines.append(personalized)
            except Exception as e:
                logger.warning("Knowledge retrieval failed for owner %s: %s", owner_id, e)
    except Exception as e:
        logger.warning("Concept extraction failed for segment: %s", e)

    if transition_ctx:
        user_lines.append(f"【用户跳转背景】{transition_ctx}")

    # Adaptive opening as passive context only
    if adaptive_opening:
        user_lines.append(f"【用户背景（仅供了解，不要在你的回复中提及）】{adaptive_opening}")

    messages = [
        {"role": "system", "content": LINE_BY_LINE_SYSTEM},
        {"role": "user", "content": "\n".join(user_lines)}
    ]

    try:
        raw = call_deepseek(messages)
        result = parse_json_response(raw)
    except Exception as e:
        raise RuntimeError(f"启动逐句讲解失败：{str(e)}")

    ai_message = result.get("message", "")
    # Hard-enforce line-by-line rules at code level (anti-spoiler, length, markdown)
    from handler_router import _sanitize_line_by_line_response
    ai_message = _sanitize_line_by_line_response(ai_message, first_segment)
    action = result.get("action", "explain")
    reason = result.get("reason", "")
    knowledge_note = _filter_meta_commentary(result.get("knowledge_note", ""))

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "reason": reason, "is_opening": bool(adaptive_opening), "knowledge_note": knowledge_note}
    })

    save_session(session)

    return {
        "session_id": session_id,
        "question": ai_message,
        "action": action,
        "sub_topic": node_name or "",
        "total_kp": 1,
        "current_kp_index": 0,
        "opening_message": "",  # LINE_BY_LINE_SYSTEM handles the first message
        "knowledge_note": knowledge_note,
    }
