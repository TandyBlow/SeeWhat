"""
Pre-processing enrichment pipeline for ALL chat modes: concept extraction,
knowledge retrieval, expansion context, definition chain — stored into
session._enriched_context. Owns the enrich_line_by_line_context alias.
"""
import logging
import sys

from chat_context import _get_recent_conversation_text, _last_user_message
from chat_enrichment_verify import _verify_concepts_via_wikipedia, _deduplicate_concepts
from chat_session import _read_uploaded_file

logger = logging.getLogger(__name__)


def enrich_chat_context(session: dict, intent: str) -> None:
    """Pre-processing pipeline for ALL chat modes.

    Extracts atomic concepts from the current content (segment in line_by_line,
    reference material in single/multi mode), searches user's knowledge point
    contents for matches, and stores enriched context in the session.
    """
    import sys
    from concept_extractor import extract_atomic_concepts, generate_expansion_context, build_definition_chain, format_concept_context
    from knowledge_retriever import build_content_index, search_user_knowledge, format_personalized_context

    chat_mode = session.get("chat_mode", "single")
    oid = session.get("owner_id", "")

    # Analyze recent conversation for ALL modes.
    # Using the reference document or current segment would anchor concepts
    # to static content, missing what's actually being discussed right now.
    text = _get_recent_conversation_text(session)
    full_doc = text

    if not text or not text.strip():
        return

    # Skip enrichment if we already did this text
    segment_hash = session.get("_last_enriched_segment", "")
    new_hash = _hash_text(text)
    if segment_hash == new_hash and session.get("_enriched_context"):
        print("[ENRICH] text unchanged, skipping", file=sys.stderr)
        return

    # Clear post-response concepts from previous turn — they'll be
    # re-extracted from the new AI response when it arrives
    session.pop("_response_concepts", None)
    session.pop("_response_extraction_attempted", None)

    print(f"[ENRICH] running for mode={chat_mode} hash={new_hash[:8]}...", file=sys.stderr)

    # 0. Fetch existing child names under current node so LLM can skip them
    existing_names: list = []
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
                # Also fetch current node's own name to prevent self-referential extraction
                self_row = _conn.execute(
                    "SELECT name FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
                    (nid, oid)
                ).fetchone()
                if self_row and self_row["name"]:
                    existing_names.append(self_row["name"])
                print(f"[ENRICH] existing children: {existing_names}", file=sys.stderr)
        except Exception as _e:
            logger.warning("[ENRICH] failed to fetch existing children: %s", _e)
    elif nid:
        # Fallback: get current node name from knowledge_points in session
        kps = session.get("knowledge_points", [])
        if kps:
            node_name = kps[0].get("title", "")
            if node_name:
                existing_names.append(node_name)

    # Also merge previously extracted concept names from prior turns for cross-window dedup
    prev_enriched = session.get("_enriched_context", {}) or {}
    prev_concepts = prev_enriched.get("concepts", [])
    if prev_concepts:
        prev_names_from_enrich = [c.get("name", "") for c in prev_concepts if c.get("name")]
        existing_names = list(set(existing_names) | set(prev_names_from_enrich))
        if prev_names_from_enrich:
            print(f"[ENRICH] +{len(prev_names_from_enrich)} names from prior turn: {prev_names_from_enrich}", file=sys.stderr)

    # 1. Concept extraction (cached per text)
    result = extract_atomic_concepts(text, full_doc, existing_names)
    concepts = result.get("concepts", [])
    cross_connections = result.get("cross_connections", [])
    print(f"[ENRICH] extracted {len(concepts)} concepts", file=sys.stderr)
    for c in concepts:
        print(f"[ENRICH]   - {c.get('name', '?')} [{c.get('category', '?')}]", file=sys.stderr)

    # 1b. Wikipedia verification — filter out noise concepts
    concepts = _verify_concepts_via_wikipedia(concepts, "[ENRICH]", text)
    concepts = _deduplicate_concepts(concepts, "[ENRICH]")

    # Always build concept context — this guides the explanation regardless of user knowledge
    concept_context = format_concept_context(concepts, cross_connections)
    print(f"[ENRICH] concept_context: {len(concept_context)} chars", file=sys.stderr)

    # 2. Knowledge content retrieval — search user KPs by CONTENT, not just title
    personalized = ""
    if oid and concepts:
        try:
            index = build_content_index(oid)
            print(f"[ENRICH] content index: {len(index.entries)} entries", file=sys.stderr)
            matches = search_user_knowledge(concepts, index)
            print(f"[ENRICH] found {len(matches)} knowledge matches", file=sys.stderr)
            for m in matches:
                print(f"[ENRICH]   - {m['kp_name']} (score={m['score']:.2f})", file=sys.stderr)
            personalized = format_personalized_context(matches)
        except Exception as e:
            logger.warning("[ENRICH] knowledge retrieval failed: %s", e)
            personalized = ""

    # 3. Expansion context
    expansion = ""
    if concepts:
        try:
            expansion = generate_expansion_context(concepts, text)
            print(f"[ENRICH] expansion context: {len(expansion)} chars", file=sys.stderr)
        except Exception as e:
            logger.warning("[ENRICH] expansion generation failed: %s", e)
            expansion = ""

    # 4. Store in session
    session["_enriched_context"] = {
        "concepts": concepts,
        "concept_context": concept_context,
        "personalized_context": personalized,
        "expansion_context": expansion,
    }
    session["_last_enriched_segment"] = new_hash
    print(f"[ENRICH] stored. personalized={len(personalized)}chars, expansion={len(expansion)}chars", file=sys.stderr)

    # 5. Definition chain (only for content questions — computed on demand)
    if intent in ("content_question", "knowledge_question"):
        try:
            from knowledge_retriever import get_user_kp_names
            user_kps = get_user_kp_names(oid) if oid else set()
            def_chain = build_definition_chain(
                _last_user_message(session),
                text,
                user_kps,
            )
            if def_chain:
                session["_enriched_context"]["definition_chain"] = def_chain
        except Exception as e:
            logger.warning("[ENRICH] definition chain generation failed: %s", e)


def _get_reference_text_for_enrichment(session: dict) -> str:
    """Get the reference text for concept extraction in non-line_by_line modes."""
    oid = session.get("owner_id", "")
    file_id = session.get("file_id", "")
    reference_text = session.get("reference_text", "")

    if file_id:
        content = _read_uploaded_file(oid, file_id)
        if content:
            return content
    if reference_text.strip():
        return reference_text

    # For multi_kp mode, use current KP's source_content
    kps = session.get("knowledge_points", [])
    idx = session.get("current_index", 0)
    if kps and idx < len(kps):
        kp = kps[idx]
        return kp.get("source_content", "") or kp.get("title", "")

    return ""


def _hash_text(text: str) -> str:
    """Simple hash for comparing segment identity."""
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# Keep old name as alias for backward compatibility
enrich_line_by_line_context = enrich_chat_context
