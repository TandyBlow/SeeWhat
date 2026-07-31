"""
Learning summary generation for the learning context chain service.
"""
import logging
from typing import Dict, Any, List

# Reuse JSON parsing from chat_service
from chat_service import parse_json_response

from context_chain_llm import _call_deepseek_raw

logger = logging.getLogger(__name__)


# ── Learning summary generation ───────────────────────────────────────

LEARNING_SUMMARY_SYSTEM = """你是一个学习摘要生成器。根据对话历史，生成这个学习会话的摘要。

返回JSON：
{
  "learned_concepts": "本次对话学习的核心概念（用中文，2-3句话概括）",
  "mastery_changes": [
    {"concept_name": "概念名", "mastery_before": "new/learning/mastered", "mastery_after": "new/learning/mastered"}
  ],
  "knowledge_notes": "基于对话中所有knowledge_note汇总的完整知识笔记"
}"""


def generate_learning_summary(messages: List[Dict[str, Any]], node_name: str) -> Dict[str, Any]:
    """Generate a learning summary from conversation messages."""
    history = []
    for msg in messages[-30:]:
        role_label = "AI" if msg["role"] == "ai" else "用户"
        history.append(f"{role_label}: {msg['content']}")

    user_content = f"知识点名称：{node_name}\n\n对话历史：\n" + "\n".join(history)
    user_content += "\n\n请根据对话历史生成学习摘要。严格按照JSON格式回复。"

    messages_payload = [
        {"role": "system", "content": LEARNING_SUMMARY_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    try:
        raw = _call_deepseek_raw(messages_payload, temperature=0.5)
        return parse_json_response(raw)
    except Exception as e:
        logger.error("Learning summary generation failed, using fallback: %s", e)
        return {
            "learned_concepts": f"围绕「{node_name}」进行了对话学习",
            "mastery_changes": [],
            "knowledge_notes": "",
        }
