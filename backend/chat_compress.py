"""
Chat session compression into a node memory record (LLM summary with metadata
fallback), stored in node_chat_memories.
"""
import json
import logging
import time
from typing import Dict, Any
from uuid import uuid4

from database import get_db_ctx
from session_store import load_session, save_session

from chat_llm import call_deepseek

logger = logging.getLogger(__name__)


# ── Chat compression ──────────────────────────────────────────────────

COMPRESS_CHAT_SYSTEM = """你是一个对话压缩专家。你的任务是将一段师生对话压缩成简洁的摘要，供后续对话作为上下文参考。

# 压缩规则

1. 提取对话中讨论过的**核心知识点**（概念、定义、公式等）
2. 记录用户的**理解水平**（哪些概念已掌握，哪些还在学习中）
3. 记录用户**问过的问题**和AI的解答要点
4. 记录对话的**进度**（讨论到了哪个子话题、还剩什么没讨论）
5. 删除寒暄、过渡语、重复确认等非知识性内容
6. 直接陈述知识内容，不要加"我学到了""我问了"等前缀，用简洁的陈述句记录

# 输出格式

返回JSON：
{
  "summary": "压缩后的对话摘要（200-400字，中文），包含：已讨论的核心概念、我的理解状态、关键问答、对话进度"
}"""


def compress_chat_session(session_id: str) -> Dict[str, Any]:
    """Compress a chat session's messages into a concise summary and store it as node memory."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    messages = session.get("messages", [])
    if len(messages) < 2:
        raise ValueError("对话轮次太少，无需压缩")

    node_id = session["node_id"]
    owner_id = session["owner_id"]

    # Build conversation text
    history_lines = []
    for msg in messages:
        role_label = "AI" if msg["role"] == "ai" else "用户"
        content = msg.get("content", "")
        if content.strip():
            history_lines.append(f"{role_label}: {content}")

    conversation_text = "\n".join(history_lines)

    # Get node name
    node_name = ""
    kps = session.get("knowledge_points", [])
    if kps:
        node_name = kps[0].get("title", "")

    user_prompt = f"知识点名称：{node_name}\n\n对话历史（{len(messages)}条消息）：\n\n{conversation_text}\n\n请压缩上面的对话为简洁摘要。严格按照JSON格式回复。"

    try:
        raw = call_deepseek([
            {"role": "system", "content": COMPRESS_CHAT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])
        result = json.loads(raw)
    except Exception as e:
        logger.warning("Chat compression via DeepSeek failed, using fallback: %s", e)
        # Fallback: build a simple summary from message metadata
        result = _fallback_compress(messages, node_name)

    summary = result.get("summary", "")
    if not summary.strip():
        summary = _fallback_compress(messages, node_name).get("summary", "")

    # Store in node_chat_memories
    memory_id = str(uuid4())
    with get_db_ctx() as conn:
        conn.execute(
            """INSERT INTO node_chat_memories (id, owner_id, node_id, session_id,
               compressed_summary, message_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (memory_id, owner_id, node_id, session_id, summary, len(messages)),
        )

    # Mark session as completed
    session["status"] = "completed"
    session["last_activity_at"] = time.time()
    save_session(session)

    return {
        "memory_id": memory_id,
        "node_id": node_id,
        "summary": summary,
        "message_count": len(messages),
    }


def _fallback_compress(messages: list, node_name: str) -> dict:
    """Build a simple compression from message metadata when LLM call fails."""
    knowledge_notes = []
    topics = set()
    question_count = 0

    for msg in messages:
        meta = msg.get("metadata", {})
        if isinstance(meta, dict):
            note = meta.get("knowledge_note", "")
            if note and note.strip():
                knowledge_notes.append(note.strip())
            sub = meta.get("sub_topic", "")
            if sub and sub.strip():
                topics.add(sub.strip())
        if msg.get("role") == "user" and msg.get("content", "").strip().endswith("?"):
            question_count += 1

    parts = [f"围绕「{node_name}」进行了{len(messages)}轮对话。"]
    if topics:
        parts.append(f"讨论过的子话题：{'、'.join(topics)}。")
    if knowledge_notes:
        parts.append(f"学到的知识点：{'；'.join(knowledge_notes[-5:])}")
    parts.append(f"用户共提出了{question_count}个问题。")

    return {"summary": " ".join(parts)}
