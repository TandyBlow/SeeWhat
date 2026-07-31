"""
Session state accessors and lifecycle: read/validate a session, find the active
session by node, read uploaded file text, look up node names, and the
user-initiated end_chat (learning snapshot + consolidation).
"""
import logging
import os
import time
from typing import Dict, Any

from database import get_db_ctx
from session_store import load_session, save_session

from chat_knowledge import consolidate_knowledge_content, _get_node_content_tail
from chat_enrichment_post import _extract_mentioned_concepts

logger = logging.getLogger(__name__)


def _get_node_name(node_id: str) -> str:
    """Get the name of a node by its ID."""
    try:
        with get_db_ctx() as conn:
            row = conn.execute(
                "SELECT name FROM nodes WHERE id = ? AND is_deleted = 0",
                (node_id,),
            ).fetchone()
        return row["name"] if row else ""
    except Exception as e:
        logger.error("Failed to get node name for %s: %s", node_id, e)
        return ""


def _read_uploaded_file(owner_id: str, file_id: str) -> str | None:
    """Read the full text content of an uploaded file from disk.

    Checks .txt cache first (may contain OCR results from background processing),
    then falls back to re-parsing the original file.
    """
    import glob as glob_mod
    from file_parser import parse_file

    upload_dir = f"/tmp/acacia_uploads/{owner_id}"

    # 1. Prefer cached .txt file (written during upload, updated by background OCR)
    cache_path = os.path.join(upload_dir, f"{file_id}.txt")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            text = f.read()
        if text.strip():
            return text

    # 2. Fall back to re-parsing the original file
    pattern = os.path.join(upload_dir, f"{file_id}.*")
    matches = glob_mod.glob(pattern)
    for match in matches:
        if match == cache_path:
            continue
        try:
            return parse_file(match)
        except Exception as e:
            logger.warning("Failed to parse cached file %s: %s", match, e)
            continue
    return None


def get_chat_session(session_id: str, owner_id: str) -> Dict[str, Any]:
    """Get full chat session state for resume, with ownership validation."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")
    if session["owner_id"] != owner_id:
        raise PermissionError("无权访问此会话")

    session["last_activity_at"] = time.time()

    knowledge_points = session.get("knowledge_points", [])
    current_index = session.get("current_index", 0)
    current_kp = knowledge_points[current_index] if current_index < len(knowledge_points) else {}

    return {
        "session_id": session["session_id"],
        "node_id": session["node_id"],
        "file_id": session["file_id"],
        "messages": session["messages"],
        "generated_content": session["generated_content"],
        "status": session["status"],
        "created_at": session["created_at"],
        "last_activity_at": session["last_activity_at"],
        "total_kp": len(knowledge_points),
        "current_kp_index": current_index,
        "kp_title": current_kp.get("title", ""),
        "kp_type": current_kp.get("type", ""),
        "kp_data": {
            "source_content": current_kp.get("source_content", ""),
            "correct_definition": current_kp.get("correct_definition", ""),
            "key_example": current_kp.get("key_example", ""),
        } if current_kp else None,
        "opening_message": session.get("opening_message", ""),
        "previous_node_id": session.get("previous_node_id"),
        "transition_reason": session.get("transition_reason", ""),
    }


def get_active_session_by_node(node_id: str, owner_id: str) -> str | None:
    """Return the session_id of the most recent active session for a node, or None."""
    with get_db_ctx() as conn:
        row = conn.execute(
            """SELECT id FROM conversation_sessions
               WHERE node_id = ? AND owner_id = ? AND status = 'active'
               ORDER BY last_activity_at DESC LIMIT 1""",
            (node_id, owner_id),
        ).fetchone()
    return row["id"] if row else None


def end_chat(session_id: str) -> Dict[str, Any]:
    """Manually end a chat session (user-initiated). Generates a learning snapshot.
    Idempotent: if already completed, returns existing state without modification."""
    session = load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    already_completed = session.get("status") == "completed"

    if not already_completed:
        session["status"] = "completed"
        session["last_activity_at"] = time.time()

        session["messages"].append({
            "role": "ai",
            "content": "对话已结束。你对这个主题已经有了很好的理解！你可以随时回顾我们生成的笔记内容。",
            "timestamp": time.time(),
            "metadata": {"action": "end_conversation"}
        })

        save_session(session)

    # Generate learning snapshot (skip if already completed)
    if not already_completed:
        try:
            from context_chain_service import generate_learning_summary, record_learning_snapshot
            node_name = ""
            kps = session.get("knowledge_points", [])
            if kps:
                node_name = kps[0].get("title", "")
            summary = generate_learning_summary(session["messages"], node_name)
            record_learning_snapshot(
                owner_id=session["owner_id"],
                node_id=session["node_id"],
                session_id=session_id,
                learned_concepts=summary.get("learned_concepts", ""),
                mastery_changes=summary.get("mastery_changes", []),
                knowledge_notes=summary.get("knowledge_notes", ""),
            )
        except Exception as e:
            logger.warning("Learning snapshot recording failed for session %s: %s", session_id, e)

    # Consolidate knowledge notes into a clean, deduplicated document
    # Run consolidation even if already completed, in case previous attempt was empty
    consolidated_content = ""
    if not already_completed:
        try:
            node_name = ""
            kps = session.get("knowledge_points", [])
            if kps:
                node_name = kps[0].get("title", "")
            reference_text = session.get("reference_text", "")
            file_id = session.get("file_id", "")
            oid = session.get("owner_id", "")
            if file_id and not reference_text:
                reference_text = _read_uploaded_file(oid, file_id) or ""
            existing = _get_node_content_tail(
                session["node_id"], oid, tail_chars=3000
            )
            consolidated_content = consolidate_knowledge_content(
                messages=session["messages"],
                node_name=node_name,
                reference_text=reference_text,
                existing_content=existing,
            )
        except Exception as e:
            logger.warning("Knowledge consolidation failed for session %s: %s", session_id, e)

    save_session(session)

    return {
        "completed": True,
        "total_content": session["generated_content"],
        "total_kp": total_kp,
        "current_kp_index": session.get("current_index", 0),
        "consolidated_content": consolidated_content,
        "mentioned_concepts": _extract_mentioned_concepts(session),
    }
