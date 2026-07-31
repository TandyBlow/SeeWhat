"""
Line-by-line content_question / meta_question / correction / chitchat branch:
builds the segment prompt, calls the LLM, advances position, may end explanation.
"""
import logging
import time
from typing import Dict, Any

from doc_position_tracker import advance_position, get_current_segment, get_progress_context
from session_store import save_session

from chat_llm import call_deepseek, parse_json_response, _filter_meta_commentary
from chat_prompts import LINE_BY_LINE_SYSTEM
from chat_enrichment_post import _extract_mentioned_concepts
from chat_line_by_line_turn import MAX_LINE_BY_LINE_TURNS, _build_line_by_line_context_lines, _end_line_by_line

logger = logging.getLogger(__name__)


def _handle_line_by_line_question(
    session: dict,
    user_answer: str,
    intent: str,
    user_turn_count: int,
) -> Dict[str, Any]:
    """Handle the content_question / meta_question / correction / chitchat branch.

    Answers the user's question briefly, then explains the current segment
    and advances the document position.
    """
    current_segment = get_current_segment(session)
    progress = get_progress_context(session)

    context_lines = _build_line_by_line_context_lines(
        session,
        current_segment,
        progress,
        segment_instruction="当前要讲解的句子：",
        user_answer=user_answer,
        intent=intent,
        include_def_chain=True,
    )

    # Safety
    if user_turn_count >= MAX_LINE_BY_LINE_TURNS:
        return _end_line_by_line(session, "已经讲解了很多内容，今天就到这里吧。")

    eval_messages = [
        {"role": "system", "content": LINE_BY_LINE_SYSTEM},
        {"role": "user", "content": "\n".join(context_lines)}
    ]

    try:
        raw = call_deepseek(eval_messages)
        result = parse_json_response(raw)
    except Exception as e:
        raise RuntimeError(f"讲解处理失败：{str(e)}")

    ai_message = result.get("message", "")
    from handler_router import _sanitize_line_by_line_response
    ai_message = _sanitize_line_by_line_response(ai_message, current_segment)
    action = result.get("action", "explain")
    knowledge_note = _filter_meta_commentary(result.get("knowledge_note", ""))

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "reason": result.get("reason", ""), "knowledge_note": knowledge_note}
    })

    # Advance position after AI explains
    if not advance_position(session):
        action = "end_explanation"
        session["status"] = "completed"

    save_session(session)
    return {
        "action": action,
        "ai_message": ai_message,
        "sub_topic": result.get("reason", ""),
        "generated_content": "",
        "knowledge_note": knowledge_note,
        "total_kp": 1,
        "current_kp_index": 0,
        "completed": action == "end_explanation",
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }
