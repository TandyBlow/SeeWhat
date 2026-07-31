"""
Persistence and tracking layer for the learning context chain.
Records navigation transitions and learning snapshots in SQLite,
walks backward to build the chain that led to a node, finds new
learnings since last visit, and renders the natural-language
transition-context string used by the opening generator.
"""
import json
from typing import Dict, Any, List
from uuid import uuid4

from database import get_db_ctx


# ── Transition recording ──────────────────────────────────────────────

def record_transition(
    owner_id: str,
    from_node_id: str | None,
    to_node_id: str,
    transition_type: str = "navigation",
    reason: str = "",
    session_id: str | None = None
) -> str:
    tid = str(uuid4())
    with get_db_ctx() as conn:
        conn.execute(
            """INSERT INTO context_transitions (id, owner_id, from_node_id, to_node_id,
               transition_type, reason, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tid, owner_id, from_node_id, to_node_id, transition_type, reason, session_id),
        )
    return tid


def get_recent_transitions(owner_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    with get_db_ctx() as conn:
        rows = conn.execute(
            """SELECT * FROM context_transitions
               WHERE owner_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (owner_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_chain_to_node(owner_id: str, to_node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
    """Walk backwards through transitions to build the chain that led to this node."""
    chain: List[Dict[str, Any]] = []
    current_to = to_node_id
    visited = set()
    with get_db_ctx() as conn:
        for _ in range(max_depth):
            row = conn.execute(
                """SELECT ct.*, n.name as to_node_name,
                   n2.name as from_node_name
                   FROM context_transitions ct
                   LEFT JOIN nodes n ON ct.to_node_id = n.id
                   LEFT JOIN nodes n2 ON ct.from_node_id = n2.id
                   WHERE ct.owner_id = ? AND ct.to_node_id = ?
                   ORDER BY ct.created_at DESC LIMIT 1""",
                (owner_id, current_to),
            ).fetchone()
            if not row:
                break
            r = dict(row)
            if r["id"] in visited:
                break
            visited.add(r["id"])
            chain.append(r)
            if not r["from_node_id"]:
                break
            current_to = r["from_node_id"]
    chain.reverse()
    return chain


def get_new_learnings_since_last_visit(
    owner_id: str,
    node_id: str
) -> List[Dict[str, Any]]:
    """Find what was learned in other nodes since the last visit to node_id."""
    with get_db_ctx() as conn:
        # Find the most recent transition TO node_id
        last_visit = conn.execute(
            """SELECT created_at FROM context_transitions
               WHERE owner_id = ? AND to_node_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (owner_id, node_id),
        ).fetchone()

        if not last_visit:
            return []

        # Find learning snapshots in OTHER nodes created after that timestamp
        rows = conn.execute(
            """SELECT nls.*, n.name as node_name
               FROM node_learning_snapshots nls
               JOIN nodes n ON nls.node_id = n.id
               WHERE nls.owner_id = ? AND nls.node_id != ?
                 AND nls.created_at > ?
               ORDER BY nls.created_at DESC LIMIT 3""",
            (owner_id, node_id, last_visit["created_at"]),
        ).fetchall()

    return [dict(r) for r in rows]


# ── Learning snapshots ────────────────────────────────────────────────

def record_learning_snapshot(
    owner_id: str,
    node_id: str,
    session_id: str,
    learned_concepts: str = "",
    mastery_changes: List[Dict[str, str]] | None = None,
    created_nodes: List[str] | None = None,
    knowledge_notes: str = ""
) -> str:
    sid = str(uuid4())
    with get_db_ctx() as conn:
        conn.execute(
            """INSERT INTO node_learning_snapshots
               (id, owner_id, node_id, session_id, learned_concepts,
                mastery_changes, created_nodes, knowledge_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sid, owner_id, node_id, session_id, learned_concepts,
                json.dumps(mastery_changes or [], ensure_ascii=False),
                json.dumps(created_nodes or [], ensure_ascii=False),
                knowledge_notes,
            ),
        )
    return sid


# ── Transition context builder ────────────────────────────────────────

def build_transition_context_text(
    owner_id: str,
    current_node_id: str,
    previous_node_id: str | None,
    transition_type: str,
    transition_reason: str
) -> str:
    """Build a natural-language context string describing the user's journey."""
    with get_db_ctx() as conn:
        cur_name = _node_name(conn, current_node_id) or "未知知识点"
        prev_name = _node_name(conn, previous_node_id) if previous_node_id else None

    type_labels = {
        "navigation": "导航",
        "mark_concept": "标记概念",
        "return": "返回",
        "initial": "首次进入",
    }
    type_label = type_labels.get(transition_type, transition_type)

    parts = []
    if prev_name:
        parts.append(f"用户从「{prev_name}」通过{type_label}跳转到「{cur_name}」。")
    else:
        parts.append(f"用户首次进入「{cur_name}」。")

    if transition_reason:
        parts.append(f"跳转原因：{transition_reason}")

    # Also include the full chain for deeper context
    chain = get_chain_to_node(owner_id, current_node_id, max_depth=5)
    if len(chain) >= 2:
        chain_names = []
        for t in chain:
            name = t.get("to_node_name") or t["to_node_id"]
            chain_names.append(name)
        parts.append(f"完整学习路径：{' → '.join(chain_names)}")

    return "\n".join(parts)


def _node_name(conn, node_id: str) -> str | None:
    row = conn.execute("SELECT name FROM nodes WHERE id = ?", (node_id,)).fetchone()
    return row["name"] if row else None
