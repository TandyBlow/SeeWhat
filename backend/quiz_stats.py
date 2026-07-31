"""
Read-side queries for the SQLite quiz backend.
Question listings, wrong-question history, single-question detail, and per-node stats.
"""
import json
import sqlite3

from quiz_sqlite import TYPE_LABELS
from review_service_sqlite import _calculate_retrievability


def get_questions_by_node_sqlite(node_id: str, owner_id: str, conn: sqlite3.Connection) -> list[dict]:
    """Get all persisted questions for a node (without revealing correct_index)."""
    rows = conn.execute(
        """SELECT qq.id, qq.question, qq.options, qq.explanation,
                   qq.question_type, qq.difficulty, qq.created_at,
                   COALESCE(qr.is_correct, -1) as last_result
           FROM quiz_questions qq
           LEFT JOIN quiz_records qr ON qr.question_id = qq.id
               AND qr.id = (SELECT id FROM quiz_records
                            WHERE question_id = qq.id AND owner_id = ?
                            ORDER BY answered_at DESC LIMIT 1)
           WHERE qq.node_id = ? AND qq.owner_id = ?
           ORDER BY qq.created_at DESC""",
        (owner_id, node_id, owner_id),
    ).fetchall()

    results = []
    for r in rows:
        options = r["options"]
        try:
            options = json.loads(options)
        except (json.JSONDecodeError, TypeError):
            pass
        results.append({
            "id": r["id"],
            "question": r["question"],
            "options": options,
            "explanation": r["explanation"],
            "question_type": r["question_type"],
            "type_label": TYPE_LABELS.get(r["question_type"], "单选题"),
            "difficulty": r["difficulty"],
            "created_at": r["created_at"],
            "answered": r["last_result"] != -1,
            "last_correct": r["last_result"] == 1,
        })
    return results


def get_wrong_questions_sqlite(owner_id: str, conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """Get questions the user got wrong, ordered by most recent wrong answer."""
    rows = conn.execute(
        """SELECT DISTINCT qq.id, qq.node_id, qq.question, qq.options, qq.explanation,
                   qq.question_type, qq.difficulty, qq.created_at
           FROM quiz_questions qq
           INNER JOIN quiz_records qr ON qr.question_id = qq.id
           WHERE qq.owner_id = ? AND qr.is_correct = 0
           ORDER BY qr.answered_at DESC
           LIMIT ?""",
        (owner_id, limit),
    ).fetchall()

    results = []
    for r in rows:
        options = r["options"]
        try:
            options = json.loads(options)
        except (json.JSONDecodeError, TypeError):
            pass
        results.append({
            "id": r["id"],
            "node_id": r["node_id"],
            "question": r["question"],
            "options": options,
            "explanation": r["explanation"],
            "question_type": r["question_type"],
            "type_label": TYPE_LABELS.get(r["question_type"], "单选题"),
            "difficulty": r["difficulty"],
        })
    return results


def get_single_question_sqlite(question_id: str, owner_id: str, conn: sqlite3.Connection) -> dict:
    """Get a single question by ID, including correct_index for quiz mode."""
    row = conn.execute(
        "SELECT id, node_id, question, options, correct_index, explanation, question_type, difficulty, created_at "
        "FROM quiz_questions WHERE id = ? AND owner_id = ?",
        (question_id, owner_id),
    ).fetchone()
    if not row:
        raise ValueError("Question not found")

    options = row["options"]
    try:
        options = json.loads(options)
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "id": row["id"],
        "node_id": row["node_id"],
        "question": row["question"],
        "options": options,
        "correct_index": row["correct_index"],
        "explanation": row["explanation"],
        "question_type": row["question_type"],
        "type_label": TYPE_LABELS.get(row["question_type"], "单选题"),
        "difficulty": row["difficulty"],
    }


# ── Quiz statistics ───────────────────────────────────────────────

def get_quiz_stats_sqlite(owner_id: str, conn: sqlite3.Connection) -> dict:
    """Get quiz statistics: per-node mastery (dynamic R(t)) and question counts."""
    rows = conn.execute(
        "SELECT id, name, stability, last_review_at, difficulty, review_count, review_state, depth FROM nodes WHERE owner_id = ? AND is_deleted = 0",
        (owner_id,),
    ).fetchall()

    nodes = []
    for r in rows:
        S = float(r["stability"] or 0)
        last = r["last_review_at"] or None
        R = _calculate_retrievability(S, last)
        q_count = conn.execute(
            "SELECT COUNT(*) FROM quiz_questions WHERE node_id = ? AND owner_id = ?",
            (r["id"], owner_id),
        ).fetchone()[0]
        nodes.append({
            "id": r["id"],
            "name": r["name"],
            "mastery_score": round(R, 4),
            "stability": round(S, 4),
            "difficulty": round(float(r["difficulty"] or 0.3), 4),
            "review_count": int(r["review_count"] or 0),
            "review_state": r["review_state"] or "new",
            "depth": r["depth"],
            "question_count": q_count,
        })

    total_questions = conn.execute(
        "SELECT COUNT(*) FROM quiz_questions WHERE owner_id = ?", (owner_id,),
    ).fetchone()[0]

    total_answers = conn.execute(
        "SELECT COUNT(*) FROM quiz_records WHERE owner_id = ?", (owner_id,),
    ).fetchone()[0]

    return {
        "nodes": nodes,
        "total_questions": total_questions,
        "total_answers": total_answers,
    }
