"""
Search/present side of the knowledge retriever for line-by-line chat mode.
Dedupe-and-rank matches across concepts via index.search, format
personalized context for the AI prompt, and fetch user KP names.
"""
from knowledge_index import KnowledgeIndex


def search_user_knowledge(
    concepts: list[dict],
    index: KnowledgeIndex,
    threshold: float = 0.10,
) -> list[dict]:
    """Search user knowledge for matches against extracted concepts.

    Args:
        concepts: List of concept dicts from extract_atomic_concepts().
        index: A KnowledgeIndex built by build_content_index().
        threshold: Minimum Jaccard similarity (0.0-1.0).

    Returns:
        List of unique matches across all concepts, sorted by score.
    """
    if not concepts or not index.entries:
        return []

    seen: set = set()
    all_matches = []
    for concept in concepts:
        matches = index.search(concept, threshold)
        for m in matches:
            key = m["kp_name"]
            if key not in seen:
                seen.add(key)
                all_matches.append(m)

    all_matches.sort(key=lambda m: m["score"], reverse=True)
    return all_matches


def format_personalized_context(matches: list[dict]) -> str:
    """Format knowledge matches as structured context for the AI prompt.

    The context presents specific connections between the user's existing
    knowledge and the current content, using the user's own words where available.

    Args:
        matches: List of match dicts from search_user_knowledge().

    Returns:
        Formatted string for injection into the AI prompt, or empty string
        if no matches (no forced connections).
    """
    if not matches:
        return ""

    lines = ["【个性化知识关联】（以下展示用户已有知识与当前内容的真实关联，解释时自然地融入）"]
    for m in matches:
        kp_name = m["kp_name"]
        snippet = m["content_snippet"]
        why = m["why"]
        lines.append(f"\n  📎 {why}")
        lines.append(f"     知识点：「{kp_name}」")
        if snippet:
            # Truncate snippet for readability
            short = snippet[:150].replace("\n", " ")
            lines.append(f"     用户笔记片段：「{short}...」" if len(snippet) > 150 else f"     用户笔记片段：「{short}」")

    return "\n".join(lines)


def get_user_kp_names(owner_id: str) -> set:
    """Get the set of knowledge point names for a user. Used by definition chain."""
    from tree_repository_sqlite import fetch_user_nodes_with_knowledge

    nodes = fetch_user_nodes_with_knowledge(owner_id)
    return {n["name"] for n in nodes if n.get("name")}
