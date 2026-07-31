import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from routers.auth_deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatContextualStartRequest(BaseModel):
    node_id: str
    node_name: str
    reference_text: str = ""
    file_id: str = ""
    chat_mode: str = ""
    previous_node_id: str | None = None
    transition_type: str = "initial"
    transition_reason: str = ""


class RecordTransitionRequest(BaseModel):
    from_node_id: str | None = None
    to_node_id: str
    transition_type: str = "navigation"
    reason: str = ""


class GenerateOpeningRequest(BaseModel):
    node_id: str
    node_name: str
    previous_node_id: str | None = None
    transition_type: str = "initial"
    transition_reason: str = ""
    reference_text: str = ""


# --- Context Chain ---

@router.post("/chat/contextual-start")
def chat_contextual_start_endpoint(
    request: ChatContextualStartRequest,
    user: dict = Depends(get_current_user)
):
    """Start a Socratic chat with context chain awareness. Generates adaptive opening."""
    from chat_service import start_chat
    from context_chain_service import record_transition, generate_adaptive_opening

    owner_id = user["sub"]

    # 1. Record the transition
    try:
        record_transition(
            owner_id=owner_id,
            from_node_id=request.previous_node_id,
            to_node_id=request.node_id,
            transition_type=request.transition_type,
            reason=request.transition_reason,
        )
    except Exception as e:
        logger.warning("Failed to record transition for owner %s: %s", owner_id, e)

    # 2. Generate adaptive opening
    try:
        opening = generate_adaptive_opening(
            owner_id=owner_id,
            node_id=request.node_id,
            node_name=request.node_name,
            previous_node_id=request.previous_node_id,
            transition_type=request.transition_type,
            transition_reason=request.transition_reason,
            reference_text=request.reference_text,
        )
    except Exception as e:
        logger.warning("Failed to generate adaptive opening for node %s: %s", request.node_id, e)
        opening = {"opening_message": "", "opening_sub_topic": "", "opening_action": "question"}

    # 3. Start chat with context
    try:
        result = start_chat(
            request.node_id, owner_id, request.node_name,
            request.reference_text, request.file_id, request.chat_mode,
            previous_node_id=request.previous_node_id,
            transition_type=request.transition_type,
            transition_reason=request.transition_reason,
            adaptive_opening=opening.get("opening_message", ""),
        )
        # For line_by_line mode, the LINE_BY_LINE_SYSTEM prompt generates the
        # first message — don't override it with the Socratic adaptive opening.
        if request.chat_mode != "line_by_line":
            result["opening_message"] = opening.get("opening_message", "")
            result["opening_sub_topic"] = opening.get("opening_sub_topic", "")
            result["opening_action"] = opening.get("opening_action", "question")
        return result
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/context/record-transition")
def record_transition_endpoint(
    request: RecordTransitionRequest,
    user: dict = Depends(get_current_user)
):
    """Record a navigation transition between knowledge points (fire-and-forget)."""
    from context_chain_service import record_transition
    tid = record_transition(
        owner_id=user["sub"],
        from_node_id=request.from_node_id,
        to_node_id=request.to_node_id,
        transition_type=request.transition_type,
        reason=request.reason,
    )
    return {"transition_id": tid}


@router.get("/context/chain/{node_id}")
def get_context_chain_endpoint(
    node_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the context chain that led to this node, plus new learnings since last visit."""
    from context_chain_service import get_chain_to_node, get_new_learnings_since_last_visit
    chain = get_chain_to_node(user["sub"], node_id)
    new_learnings = get_new_learnings_since_last_visit(user["sub"], node_id)
    return {"chain": chain, "new_learnings_since_last_visit": new_learnings}


@router.post("/chat/generate-opening")
def generate_opening_endpoint(
    request: GenerateOpeningRequest,
    user: dict = Depends(get_current_user)
):
    """Pre-generate an adaptive opening message without starting a session."""
    from context_chain_service import generate_adaptive_opening
    try:
        opening = generate_adaptive_opening(
            owner_id=user["sub"],
            node_id=request.node_id,
            node_name=request.node_name,
            previous_node_id=request.previous_node_id,
            transition_type=request.transition_type,
            transition_reason=request.transition_reason,
            reference_text=request.reference_text,
        )
        return opening
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
