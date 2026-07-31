"""
SQLite-backed review service queries: due reviews, submit review, stats,
daily queue. All queries hit the `nodes` table.
Split from review_service_sqlite.
"""
import sqlite3
from review_fsrs import datetime_now, _calculate_retrievability, _update_fsrs_params


def get_due_reviews_sqlite(owner_id: str, conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """Get nodes due for review, ordered by retrievability ascending (most urgent first)."""
    now = datetime_now()
    rows = conn.execute(
        """SELECT id, name, content, stability, difficulty, review_count,
                  review_state, last_review_at, next_review_at, mastery_score
           FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
           ORDER BY
             CASE WHEN stability <= 0 OR last_review_at IS NULL THEN 0 ELSE 1 END,
             mastery_score ASC
           LIMIT ?""",
        (owner_id, limit),
    ).fetchall()

    results = []
    for r in rows:
        S = float(r["stability"] or 0)
        last = r["last_review_at"] or None
        R = _calculate_retrievability(S, last)
        results.append({
            "node_id": r["id"],
            "node_name": r["name"],
            "content": r["content"] or "",
            "retrievability": round(R, 4),
            "stability": round(S, 4),
            "difficulty": round(float(r["difficulty"] or 0.3), 4),
            "review_count": int(r["review_count"] or 0),
            "review_state": r["review_state"] or "new",
            "next_review_at": r["next_review_at"] or None,
        })

    # Sort: new cards first, then by retrievability ascending
    results.sort(key=lambda x: (x["stability"] > 0, x["retrievability"]))
    return results


def submit_review_sqlite(node_id: str, owner_id: str, rating: int, conn: sqlite3.Connection) -> dict:
    """Submit a review rating and update FSRS parameters."""
    # Verify ownership
    row = conn.execute(
        "SELECT id FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
        (node_id, owner_id),
    ).fetchone()
    if not row:
        raise ValueError("Node not found")

    if rating not in (1, 2, 3, 4):
        raise ValueError("Rating must be 1 (Again), 2 (Hard), 3 (Good), or 4 (Easy)")

    return _update_fsrs_params(conn, node_id, rating)


def get_review_stats_sqlite(owner_id: str, conn: sqlite3.Connection) -> dict:
    """Get review statistics for the user."""
    now = datetime_now()
    today_prefix = now[:10]  # "2026-04-26"

    total_nodes = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE owner_id = ? AND is_deleted = 0",
        (owner_id,),
    ).fetchone()[0]

    due_count = conn.execute(
        """SELECT COUNT(*) FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
             AND (stability <= 0 OR last_review_at IS NULL
                  OR next_review_at <= ?)""",
        (owner_id, now),
    ).fetchone()[0]

    today_reviewed = conn.execute(
        """SELECT COUNT(*) FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
             AND last_review_at LIKE ?""",
        (owner_id, f"{today_prefix}%"),
    ).fetchone()[0]

    stability_row = conn.execute(
        "SELECT COALESCE(AVG(stability), 0) FROM nodes WHERE owner_id = ? AND is_deleted = 0 AND stability > 0",
        (owner_id,),
    ).fetchone()
    avg_stability = float(stability_row[0] or 0)

    new_count = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE owner_id = ? AND is_deleted = 0 AND (review_state = 'new' OR review_state IS NULL)",
        (owner_id,),
    ).fetchone()[0]

    return {
        "total_nodes": total_nodes,
        "due_count": due_count,
        "today_reviewed": today_reviewed,
        "avg_stability": round(avg_stability, 2),
        "new_count": new_count,
    }


def get_daily_review_queue(owner_id: str, conn: sqlite3.Connection, new_card_limit: int = 10, max_total: int = 50) -> dict:
    """Build the daily review queue: new cards first (limited), then due review cards
    ordered by retrievability ascending (most urgent first)."""
    now = datetime_now()

    # New cards: never reviewed, limit per day
    new_rows = conn.execute(
        """SELECT id, name, content, stability, difficulty, review_count,
                  review_state, last_review_at, next_review_at, mastery_score
           FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
             AND (review_state = 'new' OR review_state IS NULL OR stability <= 0)
             AND content != ''
           ORDER BY created_at ASC
           LIMIT ?""",
        (owner_id, new_card_limit),
    ).fetchall()

    # Due review cards: past their next_review_at
    review_rows = conn.execute(
        """SELECT id, name, content, stability, difficulty, review_count,
                  review_state, last_review_at, next_review_at, mastery_score
           FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
             AND review_state IN ('review', 'relearning')
             AND stability > 0
             AND content != ''
             AND (next_review_at IS NULL OR next_review_at <= ?)
           ORDER BY mastery_score ASC
           LIMIT ?""",
        (owner_id, now, max_total - len(new_rows)),
    ).fetchall()

    def _build_item(r) -> dict:
        S = float(r["stability"] or 0)
        last = r["last_review_at"] or None
        R = _calculate_retrievability(S, last)
        return {
            "node_id": r["id"],
            "node_name": r["name"],
            "content": r["content"] or "",
            "retrievability": round(R, 4),
            "stability": round(S, 4),
            "difficulty": round(float(r["difficulty"] or 0.3), 4),
            "review_count": int(r["review_count"] or 0),
            "review_state": r["review_state"] or "new",
            "next_review_at": r["next_review_at"] or None,
        }

    queue = [_build_item(r) for r in new_rows] + [_build_item(r) for r in review_rows]

    # Count totals for stats
    total_new = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE owner_id = ? AND is_deleted = 0 AND (review_state = 'new' OR review_state IS NULL OR stability <= 0) AND content != ''",
        (owner_id,),
    ).fetchone()[0]

    total_due = conn.execute(
        """SELECT COUNT(*) FROM nodes
           WHERE owner_id = ? AND is_deleted = 0
             AND (stability <= 0 OR last_review_at IS NULL
                  OR next_review_at <= ?)""",
        (owner_id, now),
    ).fetchone()[0]

    return {
        "queue": queue,
        "stats": {
            "total_queue": len(queue),
            "new_count": len(new_rows),
            "review_count": len(review_rows),
            "total_new": total_new,
            "total_due": total_due,
        },
    }
