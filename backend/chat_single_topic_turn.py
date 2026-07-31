"""
Single-topic turn evaluation: skip branch, LLM evaluation, follow-up limits,
generated_content accumulation, and end handling with knowledge consolidation.
Owns MAX_FOLLOW_UPS and MAX_TOTAL_TURNS.
"""
import logging
import time
from typing import Dict, Any

from session_store import save_session

from chat_llm import call_deepseek, parse_json_response, _filter_meta_commentary
from chat_prompts import SINGLE_TOPIC_CHAT_SYSTEM
from chat_context import _build_conversation_context
from chat_knowledge import _get_node_content_tail, consolidate_knowledge_content
from chat_session import _read_uploaded_file
from chat_enrichment_post import _extract_mentioned_concepts

logger = logging.getLogger(__name__)

MAX_FOLLOW_UPS = 3
MAX_TOTAL_TURNS = 15


def _process_single_topic_turn(
    session: dict,
    user_answer: str,
    skip: bool,
    intent: str = "content_question",
    tone: dict = None,
    gap_warning: str = ""
) -> Dict[str, Any]:
    """Process one turn of a single-topic Socratic chat."""
    user_turn_count = sum(1 for m in session["messages"] if m["role"] == "user")

    # Fetch existing note content tail for dedup and style matching
    existing_content_tail = _get_node_content_tail(session["node_id"], session["owner_id"])

    if skip:
        # Check turn limit safety on skip too
        if user_turn_count >= MAX_TOTAL_TURNS:
            session["status"] = "completed"
            session["messages"].append({
                "role": "ai",
                "content": "我们已经聊了不少了，让我总结一下。感谢你的参与，你可以随时回顾生成的笔记内容！",
                "timestamp": time.time(),
                "metadata": {"action": "end_conversation"}
            })
            save_session(session)
            return {
                "action": "end_conversation",
                "ai_message": session["messages"][-1]["content"],
                "sub_topic": "",
                "generated_content": "",
                "total_kp": 1,
                "current_kp_index": 0,
                "completed": True,
                "total_content": session["generated_content"],
                "mentioned_concepts": _extract_mentioned_concepts(session),
            }

        session["messages"].append({
            "role": "ai",
            "content": "好的，我们换一个角度。",
            "timestamp": time.time(),
            "metadata": {"action": "skip"}
        })
        eval_messages = [
            {"role": "system", "content": SINGLE_TOPIC_CHAT_SYSTEM},
            {"role": "user", "content": _build_conversation_context(session, session["owner_id"], session["node_id"], existing_content_tail, tone, gap_warning) + "\n\n用户选择跳过当前问题。请换一个角度提出新的引导性问题。请严格按照系统提示的JSON格式回复。"}
        ]
        try:
            raw = call_deepseek(eval_messages)
            result = parse_json_response(raw)
        except Exception as e:
            raise RuntimeError(f"对话处理失败：{str(e)}")

        ai_message = result.get("message", "")
        session["messages"][-1] = {
            "role": "ai",
            "content": ai_message,
            "timestamp": time.time(),
            "metadata": {"action": "question", "sub_topic": result.get("sub_topic", "")}
        }
        save_session(session)
        return {
            "action": "question",
            "ai_message": ai_message,
            "sub_topic": result.get("sub_topic", ""),
            "generated_content": "",
            "knowledge_note": _filter_meta_commentary(result.get("knowledge_note", "")),
            "total_kp": 1,
            "current_kp_index": 0,
            "completed": False,
            "mentioned_concepts": _extract_mentioned_concepts(session),
        }

    # Evaluate user's answer
    eval_messages = [
        {"role": "system", "content": SINGLE_TOPIC_CHAT_SYSTEM},
        {"role": "user", "content": _build_conversation_context(session, session["owner_id"], session["node_id"], existing_content_tail, tone, gap_warning) + f"\n\n用户刚才的回答：{user_answer}\n\n请评估用户的回答，选择动作并回复。请严格按照系统提示的JSON格式回复。"}
    ]

    try:
        raw = call_deepseek(eval_messages)
        result = parse_json_response(raw)
    except Exception as e:
        raise RuntimeError(f"对话处理失败：{str(e)}")

    action = result.get("action", "follow_up")
    ai_message = result.get("message", "")
    generated_content = _filter_meta_commentary(result.get("generated_content", ""))
    knowledge_note = _filter_meta_commentary(result.get("knowledge_note", ""))

    # Track follow_up count for code-level safety
    if action in ("follow_up", "hint"):
        session["follow_up_count"] = session.get("follow_up_count", 0) + 1

    # Code-level safety: force-end if limits exceeded
    if session.get("follow_up_count", 0) > MAX_FOLLOW_UPS:
        action = "end_conversation"
        ai_message = ai_message or "我们已经探讨了不少，让我为你做个总结吧。"
    elif user_turn_count >= MAX_TOTAL_TURNS:
        action = "end_conversation"
        ai_message = ai_message or "我们已经聊了很多了，让我总结一下关键要点。"

    session["messages"].append({
        "role": "ai",
        "content": ai_message,
        "timestamp": time.time(),
        "metadata": {"action": action, "sub_topic": result.get("sub_topic", ""), "knowledge_note": knowledge_note}
    })

    # Store generated content (for accept action)
    if generated_content:
        if session["generated_content"]:
            session["generated_content"] += "\n\n"
        sub_topic = result.get("sub_topic", "")
        if sub_topic:
            session["generated_content"] += f"## {sub_topic}\n\n{generated_content}"
        else:
            session["generated_content"] += generated_content

    # Handle conversation-ending actions
    if action in ("end_conversation", "summarize_and_move_on"):
        session["status"] = "completed"
        save_session(session)

        # Consolidate knowledge notes into a clean, deduplicated document
        consolidated = ""
        try:
            node_name = ""
            kps = session.get("knowledge_points", [])
            if kps:
                node_name = kps[0].get("title", "")
            ref_text = session.get("reference_text", "")
            file_id = session.get("file_id", "")
            oid = session.get("owner_id", "")
            if file_id and not ref_text:
                ref_text = _read_uploaded_file(oid, file_id) or ""
            consolidated = consolidate_knowledge_content(
                messages=session["messages"],
                node_name=node_name,
                reference_text=ref_text,
                existing_content=existing_content_tail,
            )
        except Exception as e:
            logger.warning("Knowledge consolidation failed for session %s: %s", session_id, e)

    save_session(session)

    if action in ("end_conversation", "summarize_and_move_on"):
        return {
            "action": action,
            "ai_message": ai_message,
            "generated_content": generated_content,
            "knowledge_note": knowledge_note,
            "sub_topic": result.get("sub_topic", ""),
            "total_kp": 1,
            "current_kp_index": 0,
            "completed": True,
            "total_content": session["generated_content"],
            "consolidated_content": consolidated,
            "mentioned_concepts": _extract_mentioned_concepts(session),
        }

    return {
        "action": action,
        "ai_message": ai_message,
        "generated_content": generated_content,
        "knowledge_note": knowledge_note,
        "sub_topic": result.get("sub_topic", ""),
        "total_kp": 1,
        "current_kp_index": 0,
        "completed": False,
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }
