from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import get_db_ctx
from quiz_service_sqlite import (
    compute_adaptive_difficulty,
    generate_batch_questions_sqlite,
    generate_quiz_question_sqlite,
    get_questions_by_node_sqlite,
    get_quiz_stats_sqlite,
    get_single_question_sqlite,
    get_wrong_questions_sqlite,
    submit_quiz_answer_sqlite,
)
from routers.auth_deps import get_current_user

router = APIRouter()


# --- Quiz ---

class QuizAnswerRequest(BaseModel):
    is_correct: bool
    question_id: str | None = None


class BatchGenerateRequest(BaseModel):
    count: int = 5
    include_children: bool = False
    question_types: list[str] = ["single_choice"]


@router.post("/generate-question/{node_id}")
def generate_question_endpoint(
    node_id: str,
    user: dict = Depends(get_current_user),
    question_type: str = "single_choice",
):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            computed_difficulty = compute_adaptive_difficulty(conn, node_id, owner_id)
            return generate_quiz_question_sqlite(node_id, owner_id, conn, question_type, computed_difficulty)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/generate-batch/{node_id}")
def generate_batch_endpoint(node_id: str, payload: BatchGenerateRequest, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return generate_batch_questions_sqlite(
                node_id, owner_id, conn,
                count=payload.count,
                include_children=payload.include_children,
                question_types=payload.question_types,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quiz-questions/{node_id}")
def get_questions_endpoint(node_id: str, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_questions_by_node_sqlite(node_id, owner_id, conn)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quiz-questions/{node_id}/{question_id}")
def get_single_question_endpoint(node_id: str, question_id: str, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_single_question_sqlite(question_id, owner_id, conn)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/wrong-questions")
def wrong_questions_endpoint(limit: int = 20, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_wrong_questions_sqlite(owner_id, conn, limit)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/submit-answer/{node_id}")
def submit_answer_endpoint(node_id: str, payload: QuizAnswerRequest, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return submit_quiz_answer_sqlite(node_id, owner_id, payload.is_correct, conn, payload.question_id)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quiz-stats")
def quiz_stats_endpoint(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        try:
            return get_quiz_stats_sqlite(owner_id, conn)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
