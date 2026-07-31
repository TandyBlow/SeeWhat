"""
Creates a child node for a concept marked during chat, records a context-chain
transition, and the abbreviation-name warning detector.
"""
import logging
import time
from typing import Dict, Any
from uuid import uuid4

from database import get_db_ctx
from session_store import load_session, save_session

from chat_session import _get_node_name

logger = logging.getLogger(__name__)


def mark_concept_node(
    session_id: str,
    concept_name: str,
    owner_id: str
) -> Dict[str, Any]:
    """Create a child node for a concept marked during chat."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session["last_activity_at"] = time.time()
    parent_id = session["node_id"]
    child_id = str(uuid4())

    with get_db_ctx() as conn:
        # Get parent's depth and owner
        parent = conn.execute(
            "SELECT depth, owner_id FROM nodes WHERE id = ? AND is_deleted = 0",
            (parent_id,)
        ).fetchone()
        if not parent:
            raise ValueError("Parent node not found")

        # Check if a sibling with the same name already exists
        existing = conn.execute(
            "SELECT id FROM nodes WHERE owner_id = ? AND parent_id = ? AND name = ? AND is_deleted = 0",
            (owner_id, parent_id, concept_name)
        ).fetchone()
        if existing:
            child_id = existing["id"]
            is_new = False
        else:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            conn.execute(
                """INSERT INTO nodes (id, owner_id, name, content, parent_id, depth, sort_order, created_at, updated_at)
                   VALUES (?, ?, ?, '', ?, ?, 0, ?, ?)""",
                (child_id, owner_id, concept_name, parent_id, parent["depth"] + 1, now, now)
            )
            conn.execute(
                "INSERT INTO edges (parent_id, child_id, sort_order) VALUES (?, ?, 0)",
                (parent_id, child_id)
            )
            is_new = True

    # Add a note to the chat
    if is_new:
        session["messages"].append({
            "role": "ai",
            "content": f"已创建子节点「{concept_name}」。你可以随时离开去学习它，回来时我会根据你的知识树更新解释。",
            "timestamp": time.time(),
            "metadata": {"action": "concept_marked", "concept_name": concept_name, "node_id": child_id}
        })
    else:
        session["messages"].append({
            "role": "ai",
            "content": f"知识点「{concept_name}」已存在于当前主题下，无需重复创建。",
            "timestamp": time.time(),
            "metadata": {"action": "concept_already_exists", "concept_name": concept_name, "node_id": child_id}
        })

    save_session(session)

    # Record transition for context chain (only for new nodes)
    if is_new:
        try:
            from context_chain_service import record_transition
            parent_name = _get_node_name(parent_id) or "未知"
            record_transition(
                owner_id=owner_id,
                from_node_id=parent_id,
                to_node_id=child_id,
                transition_type="mark_concept",
                reason=f"在学习「{parent_name}」时标记了概念「{concept_name}」",
                session_id=session_id
            )
        except Exception as e:
            logger.warning("Transition recording failed in mark_concept_node: %s", e)

    result: Dict[str, Any] = {
        "node_id": child_id,
        "name": concept_name,
        "parent_id": parent_id,
    }
    if not is_new:
        result["already_exists"] = True

    # Warn if the concept name looks like an undefined abbreviation
    warning = detect_abbreviation_name(concept_name)
    if warning:
        result["warning"] = warning
        # Append a hint to the chat message
        session["messages"][-1]["content"] += f"\n\n{warning}"
        save_session(session)

    return result


def detect_abbreviation_name(name: str) -> str | None:
    """Check if a node name looks like an undefined abbreviation.

    Returns a warning message string if it looks like an abbreviation,
    or None if the name seems fine.
    """
    stripped = name.strip()
    # Check for pure uppercase abbreviation: 2-5 uppercase letters, no Chinese
    import re
    if re.match(r'^[A-Z]{2,5}$', stripped):
        return f"知识点名称「{stripped}」看起来像一个缩写。建议补充全称，例如「OML（Optimization Methods for Logistic regression）」或给出一句话定义。否则AI对话时无法确定这个术语的准确含义。"
    # Mixed case but short and no Chinese: could be abbreviation like "OpenMP"
    if re.match(r'^[A-Za-z]{2,6}$', stripped) and not re.search(r'[一-鿿]', stripped):
        return f"知识点名称「{stripped}」看起来像一个英文缩写或简称。如果它是缩写，建议补充完整含义，以便AI在对话中准确理解。"
    return None
