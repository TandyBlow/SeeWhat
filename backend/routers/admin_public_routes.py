from fastapi import APIRouter, Depends, HTTPException, status

from database import get_db_ctx
from routers.auth_deps import get_current_user, require_admin

router = APIRouter()


# --- Official Nodes (public) ---

@router.get("/official-nodes")
def list_official_nodes(locale: str = "zh-CN"):
    with get_db_ctx() as conn:
        rows = conn.execute(
            "SELECT id, title, title_en, sort_order FROM official_nodes "
            "WHERE is_published = 1 ORDER BY sort_order ASC"
        ).fetchall()
        results = []
        for r in rows:
            item = {"id": r["id"], "title": r["title"], "sort_order": r["sort_order"]}
            if locale == "en-US" and r["title_en"]:
                item["title"] = r["title_en"]
            results.append(item)
        return results


@router.get("/official-nodes/{node_id}")
def get_official_node(node_id: str, locale: str = "zh-CN", user: dict = Depends(get_current_user)):
    with get_db_ctx() as conn:
        row = conn.execute(
            "SELECT id, title, content, title_en, content_en, sort_order, is_published, created_at, updated_at "
            "FROM official_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official node not found")
        record = dict(row)
        if not record["is_published"]:
            try:
                require_admin(user)
            except HTTPException:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Official node not found")

        # Apply locale-aware translation
        if locale == "en-US" and record.get("title_en"):
            record["title"] = record["title_en"]
            record["content"] = record.get("content_en") or record["content"]

        return record
