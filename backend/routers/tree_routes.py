import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import get_db_ctx
from tree_repository_sqlite import fetch_user_tree_sqlite
from lsystem import generate_lsystem_skeleton
from tree_skeleton import generate_tree_skeleton as generate_sc_skeleton
from tag_service_sqlite import tag_all_nodes_sqlite
from style_service_sqlite import compute_style_sqlite
from style_generator import _cache_key, build_profile_text
from routers.auth_deps import get_current_user

router = APIRouter()

TREE_GEN_VERSION = int(os.environ.get("TREE_GEN_VERSION", "2"))


def _generate_skeleton(tree_data, canvas_w=512, canvas_h=512):
    if TREE_GEN_VERSION == 2:
        return generate_sc_skeleton(tree_data, canvas_w, canvas_h)
    return generate_lsystem_skeleton(tree_data, canvas_w, canvas_h)


# --- Tree visualization ---

class CanvasSize(BaseModel):
    canvas_w: int = 512
    canvas_h: int = 512


@router.post("/generate-tree-skeleton")
def generate_tree_skeleton_endpoint(user: dict = Depends(get_current_user), body: CanvasSize = CanvasSize()):
    owner_id = user["sub"]
    try:
        tree_data = fetch_user_tree_sqlite(owner_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    if not tree_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tree data found")

    return _generate_skeleton(tree_data, body.canvas_w, body.canvas_h)


@router.post("/tag-nodes")
def tag_nodes_endpoint(user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    try:
        return tag_all_nodes_sqlite(owner_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/style")
def get_style_endpoint(force: int = 0, user: dict = Depends(get_current_user)):
    owner_id = user["sub"]
    try:
        return compute_style_sqlite(owner_id, force=bool(force))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/backgrounds/ai/{filename}")
@router.get("/api/backgrounds/ai/{filename}")
def serve_bg_image(filename: str):
    """Serve AI-generated background images (bypasses nginx static file issues)."""
    import re
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "backgrounds", "ai", filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Background image not found")
    return FileResponse(filepath, media_type="image/png")


@router.get("/debug/profile-text")
def debug_profile_text(user: dict = Depends(get_current_user)):
    """Return the knowledge profile text used for style change detection."""
    owner_id = user["sub"]
    with get_db_ctx() as conn:
        nodes = conn.execute(
            "SELECT id, name, content, domain_tag FROM nodes "
            "WHERE owner_id = ? AND is_deleted = 0",
            (owner_id,),
        ).fetchall()

    profile_text = build_profile_text([{"name": n["name"] or "", "content": n["content"] or ""} for n in nodes])
    profile_hash = _cache_key(profile_text)

    node_breakdown = []
    for n in nodes:
        name = n["name"] or ""
        content = (n["content"] or "")[:200]
        node_breakdown.append({
            "name": name,
            "contentPreview": content,
            "domainTag": n["domain_tag"] or "",
            "hasContent": bool((n["content"] or "").strip()),
        })

    return {
        "nodeCount": len(nodes),
        "profileTextLength": len(profile_text),
        "hash": profile_hash,
        "hashShort": profile_hash[:16] + "...",
        "profileText": profile_text,
        "nodes": sorted(node_breakdown, key=lambda x: x["name"]),
    }
