"""
Regenerates the last AI message using the current knowledge tree as context,
replacing the previous AI message in the session.
"""
import logging
import time
from typing import Dict, Any

from session_store import load_session, save_session

from chat_llm import call_deepseek, parse_json_response
from chat_prompts import SINGLE_TOPIC_CHAT_SYSTEM
from chat_context import _build_conversation_context

logger = logging.getLogger(__name__)


def regenerate_with_tree_context(
    session_id: str,
    tree_context: str
) -> Dict[str, Any]:
    """Regenerate the last AI message using current knowledge tree as context."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session["last_activity_at"] = time.time()

    if not session["messages"]:
        raise ValueError("No messages to regenerate")

    # Remove the last AI message
    last_ai_idx = None
    for i in range(len(session["messages"]) - 1, -1, -1):
        if session["messages"][i]["role"] == "ai":
            last_ai_idx = i
            break

    if last_ai_idx is None:
        raise ValueError("No AI message to regenerate")

    # Keep messages up to (but not including) the last AI message
    kept_messages = session["messages"][:last_ai_idx]
    removed_message = session["messages"][last_ai_idx]

    eval_messages = [
        {"role": "system", "content": SINGLE_TOPIC_CHAT_SYSTEM},
        {"role": "user", "content": _build_conversation_context({**session, "messages": kept_messages}, session["owner_id"], session["node_id"]) +
            f"\n\n请根据上面的知识档案重新生成你刚才的回复。利用知识档案中的信息来关联用户已知的概念，"
            f"用用户已掌握的知识来类比或对比当前主题。如果知识档案中有相关的前置知识，提到它们。"
            f"保持与之前相同的对话节奏。请严格按照系统提示的JSON格式回复。"}
    ]

    try:
        raw = call_deepseek(eval_messages)
        result = parse_json_response(raw)
    except Exception as e:
        raise RuntimeError(f"重新生成失败：{str(e)}")

    action = result.get("action", "question")
    ai_message = result.get("message", "")
    generated_content = result.get("generated_content", "")

    # Replace the old AI message
    session["messages"][last_ai_idx] = {
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "sub_topic": result.get("sub_topic", ""), "regenerated": True}
    }

    # If the removed message had generated content, remove it from accumulated
    # (simplification: only regenerate the message, don't touch accumulated content)

    save_session(session)

    return {
        "action": action,
        "ai_message": ai_message,
        "generated_content": generated_content,
        "knowledge_note": result.get("knowledge_note", ""),
        "sub_topic": result.get("sub_topic", ""),
    }
