"""
Answer-submission path for the SQLite quiz backend.
Computes adaptive difficulty and records answers with FSRS updates.
"""
import sqlite3
from uuid import uuid4

from review_service_sqlite import _update_fsrs_params


def compute_adaptive_difficulty(conn: sqlite3.Connection, node_id: str, owner_id: str) -> str:
    """Compute adaptive quiz difficulty from the node's last 3 answer results.

    Rules (per CEO Plan N2 scope):
      - Last 3 answers all correct (is_correct=1) -> "hard"
      - Last 3 answers all wrong   (is_correct=0) -> "easy"
      - Mixed results or fewer than 3 records  -> "medium"
    """
    rows = conn.execute(
        "SELECT is_correct FROM quiz_records WHERE node_id = ? AND owner_id = ? "
        "ORDER BY answered_at DESC LIMIT 3",
        (node_id, owner_id),
    ).fetchall()

    if len(rows) < 3:
        return "medium"

    results = [r["is_correct"] for r in rows]
    if all(r == 1 for r in results):
        return "hard"
    elif all(r == 0 for r in results):
        return "easy"
    else:
        return "medium"


def submit_quiz_answer_sqlite(
    node_id: str,
    owner_id: str,
    is_correct: bool,
    conn: sqlite3.Connection,
    question_id: str | None = None,
) -> dict:
    """Submit an answer and update mastery_score via FSRS. question_id is optional for backward compat."""
    record_id = str(uuid4())
    conn.execute(
        "INSERT INTO quiz_records (id, node_id, owner_id, question_id, is_correct) VALUES (?, ?, ?, ?, ?)",
        (record_id, node_id, owner_id, question_id, 1 if is_correct else 0),
    )

    # Map quiz answer to FSRS rating: correct=Good(3), wrong=Again(1)
    rating = 3 if is_correct else 1
    fsrs_result = _update_fsrs_params(conn, node_id, rating)

    return {
        "mastery_score": fsrs_result["mastery_score"],
        "stability": fsrs_result["stability"],
        "retrievability": fsrs_result["retrievability"],
        "review_count": fsrs_result["review_count"],
        "next_review_at": fsrs_result["next_review_at"],
    }
