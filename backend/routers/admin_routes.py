import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import get_db_ctx
from routers.admin_public_routes import router as admin_public_router
from routers.auth_deps import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Official Nodes (admin management) ---

def _translate_official_node(title: str, content: str) -> tuple[str, str]:
    """Call DeepSeek to translate official node content from Chinese to English.
    Returns (title_en, content_en)."""
    from chat_service import call_deepseek

    prompt = json.dumps({
        "instruction": (
            "Translate the following Chinese knowledge point into fluent, idiomatic English. "
            "The content is Markdown — preserve ALL Markdown formatting, code blocks, links, "
            "and structure exactly. Produce natural, educational-quality English. "
            "Return a JSON object with keys 'title_en' and 'content_en'."
        ),
        "title": title,
        "content": content,
    }, ensure_ascii=False)

    raw = call_deepseek([{"role": "user", "content": prompt}])
    parsed = json.loads(raw)
    return parsed.get("title_en", ""), parsed.get("content_en", "")


class OfficialNodeCreate(BaseModel):
    title: str
    content: str = ""
    title_en: str = ""
    content_en: str = ""
    sort_order: float = 0
    is_published: bool = False


class OfficialNodeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    title_en: str | None = None
    content_en: str | None = None
    sort_order: float | None = None
    is_published: bool | None = None


@router.get("/admin/check")
def admin_check(user: dict = Depends(get_current_user)):
    try:
        require_admin(user)
        return {"is_admin": True}
    except HTTPException:
        return {"is_admin": False}


@router.get("/admin/official-nodes")
def admin_list_official_nodes(user: dict = Depends(require_admin)):
    with get_db_ctx() as conn:
        rows = conn.execute(
            "SELECT id, title, content, title_en, content_en, sort_order, is_published, created_at, updated_at "
            "FROM official_nodes ORDER BY sort_order ASC"
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/admin/official-nodes")
def admin_create_official_node(payload: OfficialNodeCreate, user: dict = Depends(require_admin)):
    node_id = str(uuid4())
    title_en = payload.title_en
    content_en = payload.content_en

    # Auto-translate if content provided but no English version
    if payload.content.strip() and not content_en.strip():
        try:
            title_en, content_en = _translate_official_node(payload.title.strip(), payload.content)
        except Exception as e:
            logger.warning(f"Auto-translate failed for new node {node_id}: {e}")

    with get_db_ctx() as conn:
        conn.execute(
            "INSERT INTO official_nodes (id, title, content, title_en, content_en, sort_order, is_published) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_id, payload.title.strip(), payload.content, title_en, content_en,
             payload.sort_order, int(payload.is_published)),
        )
        row = conn.execute(
            "SELECT id, title, content, title_en, content_en, sort_order, is_published, created_at, updated_at "
            "FROM official_nodes WHERE id = ?", (node_id,)
        ).fetchone()
    return dict(row)


@router.patch("/admin/official-nodes/{node_id}")
def admin_update_official_node(node_id: str, payload: OfficialNodeUpdate, user: dict = Depends(require_admin)):
    with get_db_ctx() as conn:
        existing = conn.execute(
            "SELECT id, title, content, title_en, content_en FROM official_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official node not found")

        updates = []
        values = []
        for field in ("title", "content", "title_en", "content_en", "sort_order", "is_published"):
            val = getattr(payload, field)
            if val is not None:
                if field == "is_published":
                    val = int(val)
                elif field == "title":
                    val = val.strip()
                updates.append(f"{field} = ?")
                values.append(val)
        if updates:
            values.append(node_id)
            conn.execute(
                f"UPDATE official_nodes SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?",
                values,
            )

        # Auto-translate: if content was changed and no English translation exists
        new_content = payload.content if payload.content is not None else existing["content"]
        new_title = payload.title.strip() if payload.title is not None else existing["title"]
        new_content_en = payload.content_en if payload.content_en is not None else existing["content_en"]
        new_title_en = payload.title_en if payload.title_en is not None else existing["title_en"]

        if new_content.strip() and not new_content_en.strip():
            try:
                title_en, content_en = _translate_official_node(new_title, new_content)
                conn.execute(
                    "UPDATE official_nodes SET title_en = ?, content_en = ?, updated_at = datetime('now') WHERE id = ?",
                    (title_en, content_en, node_id),
                )
                new_title_en = title_en
                new_content_en = content_en
            except Exception as e:
                logger.warning(f"Auto-translate failed for node {node_id}: {e}")

        row = conn.execute(
            "SELECT id, title, content, title_en, content_en, sort_order, is_published, created_at, updated_at "
            "FROM official_nodes WHERE id = ?", (node_id,)
        ).fetchone()
    return dict(row)


@router.delete("/admin/official-nodes/{node_id}")
def admin_delete_official_node(node_id: str, user: dict = Depends(require_admin)):
    with get_db_ctx() as conn:
        existing = conn.execute(
            "SELECT id FROM official_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official node not found")
        conn.execute("DELETE FROM official_nodes WHERE id = ?", (node_id,))
    return {"ok": True}


router.include_router(admin_public_router)
