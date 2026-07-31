"""
Public start_chat entry point and the single-topic startup flow
(adaptive opening, Wikipedia context, initial DeepSeek call).
"""
import logging
import time
from typing import Dict, Any
from uuid import uuid4

from session_store import save_session

from chat_llm import call_deepseek, parse_json_response, _filter_meta_commentary
from chat_prompts import SINGLE_TOPIC_CHAT_SYSTEM
from chat_session import _read_uploaded_file
from chat_line_by_line import _start_line_by_line

logger = logging.getLogger(__name__)


def start_chat(
    node_id: str,
    owner_id: str,
    node_name: str,
    reference_text: str = "",
    file_id: str = "",
    chat_mode: str = "",
    # Context chain parameters
    previous_node_id: str | None = None,
    transition_type: str = "initial",
    transition_reason: str = "",
    adaptive_opening: str = ""
) -> Dict[str, Any]:
    """Start a new Socratic chat. Multi-KP extraction when file_id is provided.

    chat_mode: "" (auto-detect), "line_by_line" (sequential file explanation)
    previous_node_id: the node user came from (for context chain tracking)
    transition_type: "navigation", "mark_concept", "return", or "initial"
    transition_reason: why the user navigated here
    adaptive_opening: pre-generated opening message (if empty, no special opening)
    """
    session_id = str(uuid4())

    if chat_mode == "line_by_line" and file_id:
        return _start_line_by_line(
            session_id, node_id, owner_id, file_id,
            previous_node_id=previous_node_id,
            transition_type=transition_type,
            transition_reason=transition_reason,
            adaptive_opening=adaptive_opening
        )

    return _start_single_topic(
        session_id, node_id, owner_id, node_name, reference_text, file_id,
        previous_node_id=previous_node_id,
        transition_type=transition_type,
        transition_reason=transition_reason,
        adaptive_opening=adaptive_opening
    )


def _start_single_topic(
    session_id: str,
    node_id: str,
    owner_id: str,
    node_name: str,
    reference_text: str,
    file_id: str,
    previous_node_id: str | None = None,
    transition_type: str = "initial",
    transition_reason: str = "",
    adaptive_opening: str = ""
) -> Dict[str, Any]:
    """Start a single-topic Socratic chat with optional context chain awareness."""
    from context_chain_service import build_transition_context_text

    transition_ctx = build_transition_context_text(
        owner_id, node_id, previous_node_id, transition_type, transition_reason
    ) if previous_node_id or transition_type != "initial" else ""

    session = {
        "session_id": session_id,
        "node_id": node_id,
        "owner_id": owner_id,
        "file_id": file_id,
        "reference_text": reference_text,
        "knowledge_points": [{"id": "topic", "title": node_name, "type": "concept"}],
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
        "chat_mode": "single",
        "opening_message": adaptive_opening,
        "transition_context": transition_ctx,
        "previous_node_id": previous_node_id,
        "transition_reason": transition_reason,
    }

    full_reference = reference_text
    if file_id:
        full_reference = _read_uploaded_file(owner_id, file_id) or reference_text

    # Use adaptive opening if provided, otherwise fall back to default prompt
    if adaptive_opening:
        ai_message = adaptive_opening
        action = "question"
        sub_topic = ""
        knowledge_note = ""
    else:
        # Fetch Wikipedia context for the node topic
        wiki_context = ""
        try:
            from wikipedia_service import get_article_summary, get_related_topics, format_wiki_context
            summary = get_article_summary(node_name)
            if summary:
                related = get_related_topics(node_name)
                source_label = summary.get("source_name", "Wikipedia")
                wiki_context = format_wiki_context(summary, related, source_label=source_label)
        except Exception as e:
            logger.warning("Wikipedia context fetch failed for '%s': %s", node_name, e)
            wiki_context = ""

        user_content = f"节点名称：{node_name}\n\n"
        if wiki_context:
            user_content += f"{wiki_context}\n\n"
        if full_reference.strip():
            user_content += f"参考资料：\n{full_reference}\n\n"
            user_content += "请开始苏格拉底式对话。参考资料已经定义了这个主题，请直接从资料的具体内容出发提出第一个引导性问题。不要确认或质疑主题名称——直接开始教学。请严格按照系统提示的JSON格式回复。"
        elif wiki_context:
            user_content += "请开始苏格拉底式对话。上面的Wikipedia背景知识提供了这个主题的基本信息，请自由使用这些事实。先简要介绍这个主题（1-2句话），然后提出第一个引导性问题。请严格按照系统提示的JSON格式回复。"
        else:
            user_content += "请开始苏格拉底式对话。先简要介绍这个主题（1-2句话），然后提出第一个引导性问题。请严格按照系统提示的JSON格式回复。"

        messages = [
            {"role": "system", "content": SINGLE_TOPIC_CHAT_SYSTEM},
            {"role": "user", "content": user_content}
        ]

        try:
            raw = call_deepseek(messages)
            result = parse_json_response(raw)
        except Exception as e:
            raise RuntimeError(f"启动对话失败：{str(e)}")

        ai_message = result.get("message", "")
        action = result.get("action", "question")
        sub_topic = result.get("sub_topic", "")
        knowledge_note = _filter_meta_commentary(result.get("knowledge_note", ""))

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "sub_topic": sub_topic, "is_opening": True}
    })

    save_session(session)

    return {
        "session_id": session_id,
        "question": ai_message,
        "action": action,
        "sub_topic": sub_topic,
        "total_kp": 1,
        "current_kp_index": 0,
        "kp_title": node_name,
        "kp_type": "concept",
        "opening_message": adaptive_opening,
    }
