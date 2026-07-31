"""
Brief-reply handler for the meta_question/correction/chitchat intents.
Builds its own message list using LINE_BY_LINE_ANSWER_SYSTEM, then a brief
response and back to explaining.
"""
import time

from handler_prompts import LINE_BY_LINE_ANSWER_SYSTEM
from doc_position_tracker import (
    get_current_segment,
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


@_register("line_by_line", "meta_question")
@_register("line_by_line", "correction")
@_register("line_by_line", "chitchat")
def handle_line_by_line_brief_reply(session: dict, user_input: str, intent: str,
                                     tone: dict, gap_warning: str) -> dict:
    """User asked about the system, corrected us, or chitchatted.
    Brief response then back to explaining."""
    if is_document_done(session):
        return _end_line_by_line_result(session, "文档已经讲解完毕。")

    current_segment = get_current_segment(session)
    progress = get_progress_context(session)
    ctx_window = get_context_window(session)
    pos_marker = get_position_marker(session)

    hint = ""
    if intent == "meta_question":
        hint = "\n用户问了一个关于你自身的问题。简要回答后，继续讲解当前段落。"
    elif intent == "correction":
        hint = "\n用户纠正了你。承认错误，然后继续讲解当前段落。"
    else:
        hint = "\n简短回应后，继续讲解当前段落。"

    user_lines = []
    if ctx_window:
        user_lines.append(f"【文档上下文】（当前位置附近的段落）\n{ctx_window}")
    if pos_marker:
        user_lines.append(f"【{pos_marker}】")
    if gap_warning:
        user_lines.append(gap_warning)
    if tone.get("instruction"):
        user_lines.append(tone["instruction"])
    user_lines.append(f"【{progress}】当前句子：\n\n{current_segment}")
    user_lines.append(f"\n用户说：{user_input}")
    user_lines.append(hint)

    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")

    # Read enriched context from pre-processing pipeline
    # (concept extraction + knowledge retrieval by content — already filtered by relevance)
    enriched = session.get("_enriched_context", {}) or {}
    concept_ctx = enriched.get("concept_context", "")
    personalized = enriched.get("personalized_context", "")
    expansion = enriched.get("expansion_context", "")
    if concept_ctx:
        user_lines.append(concept_ctx)
    if personalized:
        user_lines.append(personalized)
    if expansion:
        user_lines.append(expansion)

    recent = _recent_history(session, 6)
    if recent:
        user_lines.append(f"\n最近对话：\n{recent}")

    messages = [
        {"role": "system", "content": LINE_BY_LINE_ANSWER_SYSTEM},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

    raw = call_deepseek(messages)
    result = parse_json_response(raw)

    ai_message = _sanitize_line_by_line_response(
        result.get("message", ""), current_segment)
    action = result.get("action", "explain")

    # Brief replies should not advance position — user didn't confirm
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
