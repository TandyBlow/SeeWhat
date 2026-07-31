"""
Post-response concept extraction from the latest AI reply, and the
mentioned-concepts reader that feeds the clickable concept chips.
"""
import logging
import sys

from chat_enrichment_verify import _verify_concepts_via_wikipedia, _deduplicate_concepts

logger = logging.getLogger(__name__)


def _refresh_response_concepts(session: dict) -> None:
    """Post-response concept extraction.

    After the AI generates a reply, re-extract atomic concepts from the
    AI's actual teaching text. This ensures the clickable concept chips
    reflect what was just taught, rather than broad topics from the
    conversation history (which is what the pre-processing extraction sees).
    """
    import sys
    from concept_extractor import extract_atomic_concepts

    # Skip if already done this turn
    if session.get("_response_concepts"):
        return

    messages = session.get("messages", [])
    if not messages:
        return

    # Find the latest AI message
    ai_text = ""
    for m in reversed(messages):
        if m.get("role") == "ai" and m.get("content", "").strip():
            ai_text = m["content"]
            break

    if not ai_text:
        return

    # Get existing child names for dedup
    existing_names: list = []
    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")
    if oid and nid:
        try:
            from tree_repository_sqlite import get_db_ctx as _get_db_ctx
            with _get_db_ctx() as _conn:
                rows = _conn.execute(
                    "SELECT name FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
                    (oid, nid)
                ).fetchall()
                existing_names = [r["name"] for r in rows]
                # Also exclude current node's own name
                self_row = _conn.execute(
                    "SELECT name FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
                    (nid, oid)
                ).fetchone()
                if self_row and self_row["name"]:
                    existing_names.append(self_row["name"])
        except Exception as e:
            logger.warning("[ENRICH] failed to fetch existing children for dedup: %s", e)
    elif nid:
        kps = session.get("knowledge_points", [])
        if kps:
            node_name = kps[0].get("title", "")
            if node_name:
                existing_names.append(node_name)

    try:
        result = extract_atomic_concepts(ai_text, "", existing_names)
        concepts = result.get("concepts", [])
        if concepts:
            concepts = _verify_concepts_via_wikipedia(concepts, "[ENRICH-POST]", ai_text)
            concepts = _deduplicate_concepts(concepts, "[ENRICH-POST]")
        if concepts:
            session["_response_concepts"] = concepts
            print(f"[ENRICH] post-response extracted {len(concepts)} concepts from AI reply", file=sys.stderr)
            for c in concepts:
                print(f"[ENRICH]   - {c.get('name', '?')} [{c.get('category', '?')}]", file=sys.stderr)
    except Exception as e:
        logger.error("[ENRICH] post-response extraction failed: %s", e)


def _extract_mentioned_concepts(session: dict) -> list:
    """Extract mentioned concepts from the session's enriched context, excluding
    concepts that already exist as children of the current node.

    Lazily triggers post-response concept extraction from the AI's latest reply,
    so the chips reflect what was actually taught rather than broad conversation topics.
    """
    # Trigger post-response extraction if not yet done this turn
    if not session.get("_response_concepts") and not session.get("_response_extraction_attempted"):
        session["_response_extraction_attempted"] = True
        try:
            _refresh_response_concepts(session)
        except Exception as e:
            logger.warning("_refresh_response_concepts failed for session %s: %s", session.get("session_id"), e)

    enriched = session.get("_enriched_context", {}) or {}
    # Prefer post-response concepts (extracted from AI's actual reply) over
    # pre-processing concepts (extracted from conversation history before AI responded)
    raw_concepts = session.get("_response_concepts") or enriched.get("concepts", [])
    if not raw_concepts:
        return []

    # Fetch existing child names so we can skip concepts the user already has
    existing_names: set = set()
    oid = session.get("owner_id", "")
    nid = session.get("node_id", "")
    if oid and nid:
        try:
            from tree_repository_sqlite import get_db_ctx as _get_db_ctx
            with _get_db_ctx() as _conn:
                rows = _conn.execute(
                    "SELECT name FROM nodes WHERE owner_id = ? AND parent_id = ? AND is_deleted = 0",
                    (oid, nid)
                ).fetchall()
                existing_names = {r["name"] for r in rows}
                # Also exclude current node's own name
                self_row = _conn.execute(
                    "SELECT name FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
                    (nid, oid)
                ).fetchone()
                if self_row and self_row["name"]:
                    existing_names.add(self_row["name"])
        except Exception as e:
            logger.warning("Failed to fetch existing names for dedup: %s", e)
    elif nid:
        kps = session.get("knowledge_points", [])
        if kps:
            node_name = kps[0].get("title", "")
            if node_name:
                existing_names.add(node_name)

    result = []
    for c in raw_concepts:
        name = c.get("name", "")
        if name in existing_names:
            continue
        result.append({
            "name": name,
            "category": c.get("category", ""),
            "definition": c.get("definition", ""),
            "prerequisites": c.get("prerequisites", []),
            "expansion_directions": c.get("expansion_directions", []),
            "verified": c.get("verified", False),
            "wiki_summary": c.get("wiki_summary", ""),
            "wiki_description": c.get("wiki_description", ""),
        })
    return result
