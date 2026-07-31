"""
FSRS (Free Spaced Repetition Scheduler) math core.
Pure Python math + datetime helpers, no DB queries.
Split from review_service_sqlite.
"""
import math
import sqlite3
from datetime import datetime, timezone, timedelta


def datetime_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _calculate_retrievability(stability: float, last_review_at: str | None) -> float:
    """Calculate current retrievability R(t) = exp(-t / S).
    Returns 0 for new cards (S=0 or never reviewed)."""
    if not stability or stability <= 0 or not last_review_at:
        return 0.0
    try:
        last = datetime.strptime(last_review_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed_days = (now - last).total_seconds() / 86400.0
        if elapsed_days < 0:
            elapsed_days = 0
        return math.exp(-elapsed_days / stability)
    except (ValueError, OSError):
        return 0.0


def _update_fsrs_params(conn: sqlite3.Connection, node_id: str, rating: int) -> dict:
    """Core FSRS update after a review. Reads current params, applies FSRS formulas,
    writes back updated stability/difficulty/review_count/state/next_review_at,
    and sets mastery_score to current R(t).

    rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    """
    row = conn.execute(
        "SELECT stability, difficulty, review_count, review_state, last_review_at "
        "FROM nodes WHERE id = ?",
        (node_id,),
    ).fetchone()
    if not row:
        raise ValueError("Node not found")

    S = float(row["stability"] or 0)
    D = float(row["difficulty"] or 0.3)
    count = int(row["review_count"] or 0)
    state = row["review_state"] or "new"

    # ── Difficulty update ──
    D = D + 0.15 * (3 - rating) * (1 - D)
    D = max(0.01, min(1.0, D))

    # ── Stability update ──
    is_first = count == 0 or S <= 0
    if is_first:
        # First review — initial stability mapping
        if rating == 1:
            S = 0.5
        elif rating == 2:
            S = 1.0
        elif rating == 3:
            S = 2.0
        else:  # rating == 4
            S = 4.0
    else:
        if rating == 1:  # Again
            S = max(0.5, S * 0.5)
        elif rating == 2:  # Hard
            S = S * 1.3
        elif rating == 3:  # Good
            S = S * 2.5
        else:  # rating == 4 (Easy)
            S = S * 4.0

    # ── State machine ──
    if state == "new":
        state = "review"
    elif rating == 1:
        state = "relearning"
    elif state == "relearning" and rating >= 3:
        state = "review"

    # ── Next review interval ──
    # Target 90% retention: interval = S * ln(1/0.9) ≈ S * 0.10536
    interval_days = S * 0.10536
    now = datetime_now()
    next_review = _add_days(now, interval_days)

    # ── Current retrievability as mastery_score ──
    mastery = _calculate_retrievability(S, now)

    conn.execute(
        """UPDATE nodes SET
           stability = ?, difficulty = ?, review_count = ?,
           review_state = ?, last_review_at = ?, next_review_at = ?,
           mastery_score = ?, updated_at = ?
           WHERE id = ?""",
        (S, D, count + 1, state, now, next_review, mastery, now, node_id),
    )

    return {
        "node_id": node_id,
        "stability": round(S, 4),
        "difficulty": round(D, 4),
        "retrievability": round(mastery, 4),
        "mastery_score": round(mastery, 4),
        "review_count": count + 1,
        "review_state": state,
        "next_review_at": next_review,
        "last_review_at": now,
    }


def _add_days(iso_str: str, days: float) -> str:
    """Add days to an ISO datetime string, return new ISO string."""
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        result = dt + timedelta(seconds=days * 86400)
        return result.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return iso_str
