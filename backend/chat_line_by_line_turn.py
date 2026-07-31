"""
Line-by-line turn dispatcher: handles the skip/confirmation branch (advance
position, explain next segment) and the end_request branch, plus the shared
context-lines builder and the end helper. Owns MAX_LINE_BY_LINE_TURNS.
"""
import logging
import time
from typing import Dict, Any

from doc_position_tracker import advance_position, get_current_segment, get_progress_context, get_context_window, get_position_marker
from session_store import save_session

from chat_llm import call_deepseek, parse_json_response, _filter_meta_commentary
from chat_prompts import LINE_BY_LINE_SYSTEM
from chat_enrichment_post import _extract_mentioned_concepts

logger = logging.getLogger(__name__)

MAX_LINE_BY_LINE_TURNS = 30


def _build_line_by_line_context_lines(
    session: dict,
    current_segment: str,
    progress: str,
    segment_instruction: str = "请解释下面这句话：",
    user_answer: str = "",
    intent: str = "",
    include_def_chain: bool = False,
) -> list:
    """Build the shared context-lines block for a line-by-line turn.

    Used by both the skip/confirmation branch (advance + explain next segment)
    and the content-question branch. The order of the lines must be preserved.
    """
    ctx_window = get_context_window(session)
    pos_marker = get_position_marker(session)

    context_lines = []
    if ctx_window:
        context_lines.append(f"【文档上下文】（当前位置附近的段落）\n{ctx_window}")
    if pos_marker:
        context_lines.append(f"【{pos_marker}】")
    context_lines.append(f"【逐句讲解】{progress}")
    context_lines.append(f"{segment_instruction}\n\n{current_segment}")

    if user_answer:
        context_lines.append(f"\n用户说：{user_answer}")

    if intent == "content_question":
        context_lines.append("\n判断用户是缺少前置知识还是需要换角度解释。缺少前置知识→建议去学具体的原子知识点。需要换角度→直接展开，不要问。")
    elif intent == "meta_question":
        context_lines.append("\n简要回答（关于你自己的问题），然后继续讲解当前段落。")
    elif intent == "correction":
        context_lines.append("\n用户纠正了你。承认错误，然后继续讲解当前段落。")
    elif intent:
        context_lines.append("\n简短回应后，继续讲解当前段落。")

    # Inject enriched context (concept extraction + knowledge retrieval by content)
    # instead of full knowledge profile
    enriched = session.get("_enriched_context", {}) or {}
    concept_ctx = enriched.get("concept_context", "")
    personalized = enriched.get("personalized_context", "")
    expansion = enriched.get("expansion_context", "")
    def_chain = enriched.get("definition_chain", "")
    if concept_ctx:
        context_lines.append(concept_ctx)
    if personalized:
        context_lines.append(personalized)
    if expansion:
        context_lines.append(expansion)
    if include_def_chain and def_chain:
        context_lines.append(def_chain)

    # Last 3 messages for continuity
    recent = session["messages"][-6:]
    if recent:
        context_lines.append("\n最近对话：")
        for msg in recent:
            role_label = "AI" if msg["role"] == "ai" else "用户"
            context_lines.append(f"{role_label}: {msg['content']}")

    return context_lines


def _process_line_by_line_turn(
    session: dict,
    user_answer: str,
    skip: bool,
    intent: str = "content_question"
) -> Dict[str, Any]:
    """Process one turn of a line-by-line explanation chat.

    Code tracks position — AI never needs to find where it left off.
    The AI is given the exact current segment to explain.
    """
    user_turn_count = sum(1 for m in session["messages"] if m["role"] == "user")

    # ── Handle skip: advance position, explain next segment ──────────
    if skip or intent in ("skip_request", "confirmation"):
        # Advance to next segment
        if skip or intent == "skip_request":
            advance_position(session)  # skip = advance without explaining current
        # For confirmation ("嗯", "继续"), we advance and explain the next

        has_more = advance_position(session) if intent != "skip_request" else True
        if not has_more or not get_current_segment(session):
            return _end_line_by_line(session, "文档已经讲解完毕。")

        current_segment = get_current_segment(session)
        progress = get_progress_context(session)

        context_lines = _build_line_by_line_context_lines(session, current_segment, progress)

        # Safety: force end if too many turns
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

    # ── Handle end request ────────────────────────────────────────────
    if intent == "end_request":
        return _end_line_by_line(session, "好的，讲解到这里。你可以随时回来继续。")

    # ── Handle content question / meta / correction / chitchat ────────
    from chat_line_by_line_question import _handle_line_by_line_question
    return _handle_line_by_line_question(session, user_answer, intent, user_turn_count)


def _end_line_by_line(session: dict, message: str) -> Dict[str, Any]:
    """End a line-by-line explanation chat."""
    session["status"] = "completed"
    session["messages"].append({
        "role": "ai",
        "content": message,
        "timestamp": time.time(),
        "metadata": {"action": "end_explanation"}
    })
    save_session(session)
    return {
        "action": "end_explanation",
        "ai_message": message,
        "sub_topic": "",
        "generated_content": "",
        "knowledge_note": "",
        "total_kp": 1,
        "current_kp_index": 0,
        "completed": True,
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }
