from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import get_db_ctx
from routers.auth_deps import get_current_user

router = APIRouter()


class ContentUpdateRequest(BaseModel):
    content: str


class MoveRequest(BaseModel):
    new_parent_id: str | None = None


@router.patch("/nodes/{node_id}/content")
def update_content(node_id: str, payload: ContentUpdateRequest, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        row = conn.execute(
            "SELECT id FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
            (node_id, owner_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

        conn.execute(
            "UPDATE nodes SET content = ?, updated_at = datetime('now') WHERE id = ?",
            (payload.content, node_id),
        )

    return {"ok": True}


@router.delete("/nodes/{node_id}")
def delete_node(node_id: str, delete_children: bool = False, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        node = conn.execute(
            "SELECT * FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
            (node_id, owner_id),
        ).fetchone()
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

        if delete_children:
            conn.execute("UPDATE nodes SET is_deleted = 1 WHERE id = ?", (node_id,))
            _soft_delete_subtree(conn, node_id, owner_id)
            conn.execute("DELETE FROM edges WHERE parent_id = ? OR child_id = ?", (node_id, node_id))
        else:
            children = conn.execute(
                "SELECT id, sort_order FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0 ORDER BY sort_order",
                (owner_id, node_id),
            ).fetchall()

            parent_id = node["parent_id"]
            next_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM nodes WHERE owner_id = ? AND parent_id IS ? AND is_deleted = 0 AND id != ?",
                (owner_id, parent_id, node_id),
            ).fetchone()[0]

            for child in children:
                next_order += 1
                conn.execute(
                    "UPDATE nodes SET parent_id = ?, sort_order = ? WHERE id = ?",
                    (parent_id, next_order, child["id"]),
                )
                conn.execute("DELETE FROM edges WHERE child_id = ? AND parent_id = ?", (child["id"], node_id))
                if parent_id:
                    conn.execute(
                        "INSERT OR IGNORE INTO edges (parent_id, child_id, sort_order) VALUES (?, ?, ?)",
                        (parent_id, child["id"], next_order),
                    )

            conn.execute("UPDATE nodes SET is_deleted = 1 WHERE id = ?", (node_id,))
            conn.execute("DELETE FROM edges WHERE parent_id = ? OR child_id = ?", (node_id, node_id))

    return {"ok": True}


def _soft_delete_subtree(conn, parent_id: str, owner_id: str):
    children = conn.execute(
        "SELECT id FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
        (owner_id, parent_id),
    ).fetchall()
    for child in children:
        conn.execute("UPDATE nodes SET is_deleted = 1 WHERE id = ?", (child["id"],))
        conn.execute("DELETE FROM edges WHERE parent_id = ? OR child_id = ?", (child["id"], child["id"]))
        _soft_delete_subtree(conn, child["id"], owner_id)


@router.patch("/nodes/{node_id}/move")
def move_node(node_id: str, payload: MoveRequest, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    new_parent_id = payload.new_parent_id

    with get_db_ctx() as conn:
        node = conn.execute(
            "SELECT * FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
            (node_id, owner_id),
        ).fetchone()
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

        if node["parent_id"] == new_parent_id:
            return {"ok": True}

        if new_parent_id:
            parent = conn.execute(
                "SELECT id FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
                (new_parent_id, owner_id),
            ).fetchone()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New parent not found")

            if _is_descendant(conn, node_id, new_parent_id, owner_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot move node to its own descendant")

            existing = conn.execute(
                "SELECT id FROM nodes WHERE owner_id = ? AND parent_id = ? AND name = ? AND is_deleted = 0 AND id != ?",
                (owner_id, new_parent_id, node["name"], node_id),
            ).fetchone()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sibling with same name already exists at destination")

        old_parent_id = node["parent_id"]
        if old_parent_id:
            conn.execute("DELETE FROM edges WHERE parent_id = ? AND child_id = ?", (old_parent_id, node_id))

        next_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM nodes WHERE owner_id = ? AND parent_id IS ? AND is_deleted = 0",
            (owner_id, new_parent_id),
        ).fetchone()[0] + 1

        conn.execute(
            "UPDATE nodes SET parent_id = ?, sort_order = ?, updated_at = datetime('now') WHERE id = ?",
            (new_parent_id, next_order, node_id),
        )

        if new_parent_id:
            conn.execute(
                "INSERT OR IGNORE INTO edges (parent_id, child_id, sort_order) VALUES (?, ?, ?)",
                (new_parent_id, node_id, next_order),
            )

    return {"ok": True}


def _is_descendant(conn, ancestor_id: str, candidate_id: str, owner_id: str) -> bool:
    children = conn.execute(
        "SELECT id FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
        (owner_id, ancestor_id),
    ).fetchall()
    for child in children:
        if child["id"] == candidate_id:
            return True
        if _is_descendant(conn, child["id"], candidate_id, owner_id):
            return True
    return False
