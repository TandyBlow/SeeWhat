"""
Core generation service for the SQLite quiz backend.
Writes rows to quiz_questions and exposes the single/batch generation entry points.
"""
import json
import sqlite3
from uuid import uuid4

from quiz_llm import BATCH_PROMPT, PROMPTS, call_llm
from quiz_parse import PARSERS, parse_batch

TYPE_LABELS = {
    "single_choice": "单选题",
    "true_false": "判断题",
    "short_answer": "简答题",
}


# ── Persistence helpers ───────────────────────────────────────────

def _persist_question(
    conn: sqlite3.Connection,
    node_id: str,
    owner_id: str,
    question: str,
    options: str,
    correct_index: int,
    explanation: str,
    question_type: str,
    difficulty: str = "medium",
) -> str:
    qid = str(uuid4())
    conn.execute(
        """INSERT INTO quiz_questions
           (id, node_id, owner_id, question, options, correct_index, explanation, question_type, difficulty)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (qid, node_id, owner_id, question, options, correct_index, explanation, question_type, difficulty),
    )
    return qid


def _node_to_input(name: str, content: str) -> str:
    parts = [f"知识点名称：{name}"]
    if content:
        parts.append(f"内容：{content}")
    return "\n".join(parts)


def _collect_node_content(conn: sqlite3.Connection, node_id: str, owner_id: str) -> list[dict]:
    """Recursively collect a node and its descendants' name+content."""
    rows = conn.execute(
        "SELECT id, name, content FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
        (owner_id, node_id),
    ).fetchall()
    result = [{"name": rows[0]["name"] if rows else "", "content": ""}]
    if rows:
        result = []
        for r in rows:
            result.append({"name": r["name"], "content": r["content"] or ""})
            result.extend(_collect_node_content(conn, r["id"], owner_id))
    return result


# ── Public API ────────────────────────────────────────────────────

def generate_quiz_question_sqlite(
    node_id: str,
    owner_id: str,
    conn: sqlite3.Connection,
    question_type: str = "single_choice",
    difficulty: str = "medium",
) -> dict:
    """Generate a single question and persist it. Backward-compatible with old signature."""
    row = conn.execute(
        "SELECT name, content FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
        (node_id, owner_id),
    ).fetchone()
    if not row:
        raise ValueError("Node not found")

    user_input = _node_to_input(row["name"], row["content"] or "")

    if question_type not in PARSERS:
        question_type = "single_choice"

    system_prompt = PROMPTS[question_type]
    raw = call_llm(user_input, system_prompt)
    quiz = PARSERS[question_type](raw)

    qid = _persist_question(
        conn, node_id, owner_id,
        question=quiz["question"],
        options=quiz["options"] if isinstance(quiz["options"], str) else json.dumps(quiz["options"]),
        correct_index=quiz["correct_index"],
        explanation=quiz.get("explanation", ""),
        question_type=question_type,
        difficulty=difficulty,
    )
    quiz["id"] = qid
    quiz["node_id"] = node_id
    quiz["difficulty"] = difficulty

    # Convert options back to list for API response
    if isinstance(quiz["options"], str):
        try:
            quiz["options"] = json.loads(quiz["options"])
        except json.JSONDecodeError:
            pass

    quiz["type_label"] = TYPE_LABELS.get(question_type, "单选题")
    return quiz


def generate_batch_questions_sqlite(
    node_id: str,
    owner_id: str,
    conn: sqlite3.Connection,
    count: int = 5,
    include_children: bool = False,
    question_types: list[str] | None = None,
) -> dict:
    """Generate multiple questions at once, optionally from children too."""
    if question_types is None:
        question_types = ["single_choice"]

    row = conn.execute(
        "SELECT name, content FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
        (node_id, owner_id),
    ).fetchone()
    if not row:
        raise ValueError("Node not found")

    parts = [_node_to_input(row["name"], row["content"] or "")]
    if include_children:
        children = _collect_node_content(conn, node_id, owner_id)
        for child in children:
            parts.append(_node_to_input(child["name"], child["content"]))

    user_input = "\n---\n".join(parts)
    type_desc = "、".join(TYPE_LABELS.get(t, t) for t in question_types)
    system_prompt = BATCH_PROMPT.format(count=count, type_desc=type_desc)
    # Hint the LLM about which types to mix
    type_hint = "、".join(question_types)
    user_input = f"题目类型要求：请生成{type_hint}。\n\n{user_input}"

    raw = call_llm(user_input, system_prompt, temperature=0.9)
    questions = parse_batch(raw)

    results = []
    for q in questions[:count]:
        qtype = q.get("question_type", "single_choice")
        if qtype not in PARSERS:
            qtype = "single_choice"
        qid = _persist_question(
            conn, node_id, owner_id,
            question=q["question"],
            options=q["options"] if isinstance(q["options"], str) else json.dumps(q.get("options", [])),
            correct_index=q["correct_index"],
            explanation=q.get("explanation", ""),
            question_type=qtype,
            difficulty=q.get("difficulty", "medium"),
        )
        result = {
            "id": qid,
            "node_id": node_id,
            "question": q["question"],
            "options": q["options"] if not isinstance(q["options"], str) else json.loads(q["options"]),
            "correct_index": q["correct_index"],
            "explanation": q["explanation"],
            "question_type": qtype,
            "difficulty": q.get("difficulty", "medium"),
            "type_label": TYPE_LABELS.get(qtype, "单选题"),
        }
        results.append(result)

    return {"node_id": node_id, "questions": results}
