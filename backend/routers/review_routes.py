import random
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import get_db_ctx
from quiz_service_sqlite import compute_adaptive_difficulty, generate_quiz_question_sqlite
from review_service_sqlite import (
    get_daily_review_queue,
    get_due_reviews_sqlite,
    submit_review_sqlite,
    get_review_stats_sqlite,
)
from routers.auth_deps import get_current_user

router = APIRouter()


class ReviewRequest(BaseModel):
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy


# --- Daily Review ---

class DailyQuizCompleteRequest(BaseModel):
    pass


def _get_today_date() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def _get_refresh_at() -> str:
    from datetime import datetime, timedelta
    now = datetime.now()
    today_630 = now.replace(hour=6, minute=30, second=0, microsecond=0)
    if now < today_630:
        return today_630.isoformat()
    return (today_630 + timedelta(days=1)).isoformat()


def _pick_question_type(review_state: str) -> str:
    """Pick question type based on review state.
    New nodes: easier recognition (true_false or single_choice).
    Relearning nodes: active recall (short_answer).
    Review nodes: random among all three."""
    import random
    if review_state == 'new':
        return random.choice(['true_false', 'single_choice'])
    elif review_state == 'relearning':
        return 'short_answer'
    else:
        return random.choice(['single_choice', 'true_false', 'short_answer'])


@router.get("/daily-quiz/status")
def daily_quiz_status(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    refresh_at = _get_refresh_at()
    with get_db_ctx() as conn:
        stats = get_review_stats_sqlite(owner_id, conn)
        return {
            "due_count": stats["due_count"],
            "today_reviewed": stats["today_reviewed"],
            "new_count": stats["new_count"],
            "refresh_at": refresh_at,
        }


@router.get("/daily-review/queue")
def daily_review_queue(
    new_card_limit: int = 10,
    max_total: int = 50,
    user: dict = Depends(get_current_user),
):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_daily_review_queue(owner_id, conn, new_card_limit, max_total)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/daily-review/generate-question")
def daily_review_generate_question(
    payload: dict = None,
    user: dict = Depends(get_current_user),
):
    import random
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        if payload and "node_id" in payload:
            node_id = payload["node_id"]
            # Verify ownership
            row = conn.execute(
                "SELECT id, review_state FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
                (node_id, owner_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识点不存在")
            review_state = row["review_state"] or "new"
            question_type = payload.get("question_type") or _pick_question_type(review_state)
        else:
            # Fallback: random node (backward compatibility)
            nodes = conn.execute(
                """SELECT id FROM nodes
                   WHERE owner_id = ? AND is_deleted = 0 AND content != ''
                   ORDER BY RANDOM() LIMIT 1""",
                (owner_id,),
            ).fetchall()
            if not nodes:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="没有可用的知识点")
            node_id = nodes[0]["id"]
            question_type = random.choice(["single_choice", "true_false", "short_answer"])

        try:
            computed_difficulty = compute_adaptive_difficulty(conn, node_id, owner_id)
            return generate_quiz_question_sqlite(node_id, owner_id, conn, question_type, computed_difficulty)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/daily-quiz/complete")
def daily_quiz_complete(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    today = _get_today_date()
    completion_id = str(uuid4())
    with get_db_ctx() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_quiz_completion (id, user_id, date, completed, completed_at)
               VALUES (?, ?, ?, 1, datetime('now'))""",
            (completion_id, owner_id, today),
        )
        return {"completed": True, "date": today}


@router.post("/daily-quiz/reset")
def daily_quiz_reset(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    from review_service_sqlite import datetime_now
    now = datetime_now()
    utc_prefix = now[:10]
    local_date = _get_today_date()
    with get_db_ctx() as conn:
        # Clear today's completion marker
        conn.execute(
            "DELETE FROM daily_quiz_completion WHERE user_id = ? AND date = ?",
            (owner_id, local_date),
        )
        # Clear all quiz records for this user
        conn.execute(
            "DELETE FROM quiz_records WHERE owner_id = ?",
            (owner_id,),
        )
        # Reset all non-deleted nodes for this user back to new
        conn.execute(
            """UPDATE nodes SET last_review_at = NULL, next_review_at = NULL,
               review_state = 'new', stability = 0, difficulty = 0.3, review_count = 0
               WHERE owner_id = ? AND is_deleted = 0""",
            (owner_id,),
        )
        return {"reset": True, "utc_date": utc_prefix, "local_date": local_date}


@router.get("/due-reviews")
def due_reviews_endpoint(limit: int = 20, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_due_reviews_sqlite(owner_id, conn, limit)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/review/{node_id}")
def review_endpoint(node_id: str, payload: ReviewRequest, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return submit_review_sqlite(node_id, owner_id, payload.rating, conn)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/review-stats")
def review_stats_endpoint(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_review_stats_sqlite(owner_id, conn)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
