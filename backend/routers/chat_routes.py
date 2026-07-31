from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from routers.auth_deps import get_current_user
from routers.upload_routes import _cleanup_uploaded_file

router = APIRouter()


# --- Chat (single-topic Socratic dialogue) ---

class ChatStartRequest(BaseModel):
    node_id: str
    node_name: str
    reference_text: str = ""
    file_id: str = ""
    chat_mode: str = ""  # "" (auto), "line_by_line" (sequential file explanation)


class ChatTurnRequest(BaseModel):
    session_id: str
    user_answer: str
    skip: bool = False


class ChatRegenerateRequest(BaseModel):
    session_id: str
    tree_context: str = ""


class ChatMarkConceptRequest(BaseModel):
    session_id: str
    concept_name: str


class ChatEndRequest(BaseModel):
    session_id: str


@router.post("/chat/start")
def chat_start_endpoint(
    request: ChatStartRequest,
    user: dict = Depends(get_current_user)
):
    """Start a Socratic chat for a single node topic."""
    from chat_service import start_chat
    owner_id = user["sub"]
    try:
        return start_chat(
            request.node_id,
            owner_id,
            request.node_name,
            request.reference_text,
            request.file_id,
            request.chat_mode
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/chat/turn")
def chat_turn_endpoint(
    request: ChatTurnRequest,
    user: dict = Depends(get_current_user)
):
    """Process one turn of a Socratic chat."""
    from chat_service import process_chat_turn
    try:
        return process_chat_turn(request.session_id, request.user_answer, request.skip)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/chat/regenerate")
def chat_regenerate_endpoint(
    request: ChatRegenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Regenerate the last AI message with current knowledge tree context."""
    from chat_service import regenerate_with_tree_context
    try:
        return regenerate_with_tree_context(request.session_id, request.tree_context)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/chat/mark-concept")
def chat_mark_concept_endpoint(
    request: ChatMarkConceptRequest,
    user: dict = Depends(get_current_user)
):
    """Mark a concept during chat, creating a child node."""
    from chat_service import mark_concept_node
    owner_id = user["sub"]
    try:
        return mark_concept_node(request.session_id, request.concept_name, owner_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/chat/end")
def chat_end_endpoint(
    request: ChatEndRequest,
    user: dict = Depends(get_current_user)
):
    """Manually end a Socratic chat session."""
    from chat_service import end_chat
    from session_store import load_session
    try:
        # Clean up uploaded file associated with this session
        session = load_session(request.session_id)
        if session:
            file_id = session.get("file_id", "")
            if file_id:
                _cleanup_uploaded_file(session.get("owner_id", user["sub"]), file_id)
        result = end_chat(request.session_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


class ChatCompressRequest(BaseModel):
    session_id: str


@router.post("/chat/compress")
def chat_compress_endpoint(
    request: ChatCompressRequest,
    user: dict = Depends(get_current_user)
):
    """Compress a chat session into a summary and store as node memory, then clear."""
    from chat_service import compress_chat_session
    try:
        return compress_chat_session(request.session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/chat/sessions/{session_id}")
def get_chat_session_endpoint(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    """Get full chat session state for resume."""
    from chat_service import get_chat_session
    try:
        return get_chat_session(session_id, user["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或已过期"
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/chat/sessions/by-node/{node_id}")
def get_chat_session_by_node(
    node_id: str,
    user: dict = Depends(get_current_user)
):
    """Find the most recent active chat session for a node."""
    from chat_service import get_active_session_by_node
    session_id = get_active_session_by_node(node_id, user["sub"])
    return {"session_id": session_id}
