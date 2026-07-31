"""
Builds the full user knowledge-tree profile string (mastered/learning/new
categorization, path to root, siblings/children) for AI prompts.
"""
from tree_repository_sqlite import fetch_user_nodes_with_knowledge


def build_knowledge_profile(owner_id: str, current_node_id: str) -> str:
    """Build a full knowledge profile string for the AI prompt.

    Includes ALL user nodes categorized by mastery level.
    No pruning, no limits — the profile is a complete mirror of the user's knowledge tree.
    """
    from tree_repository_sqlite import fetch_user_nodes_with_knowledge

    nodes = fetch_user_nodes_with_knowledge(owner_id)
    if not nodes:
        return ""

    # Build lookup maps
    node_by_id = {n["id"]: n for n in nodes}
    children_map: dict[str, list[dict]] = {}
    for n in nodes:
        pid = n["parent_id"]
        if pid:
            children_map.setdefault(pid, []).append(n)

    # Build path to root for current node
    path_to_root: list[dict] = []
    current = node_by_id.get(current_node_id)
    visited = set()
    while current and current["id"] not in visited:
        visited.add(current["id"])
        path_to_root.append(current)
        current = node_by_id.get(current["parent_id"]) if current["parent_id"] else None
    path_to_root.reverse()

    # Categorize every node
    mastered: list[dict] = []
    learning: list[dict] = []
    new_nodes: list[dict] = []
    for n in nodes:
        score = n["mastery_score"]
        state = n["review_state"]
        count = n["review_count"]
        if score > 0.7:
            mastered.append(n)
        elif score >= 0.3 or (count > 0 and state != "new"):
            learning.append(n)
        else:
            new_nodes.append(n)

    lines: list[str] = []
    lines.append("【用户知识档案】")

    # ── A: Current Topic Context ──
    cur = node_by_id.get(current_node_id)
    if cur:
        lines.append(f"当前主题：{cur['name']}")
        if cur["domain_tag"]:
            lines.append(f"所属领域：{cur['domain_tag']}")

        if len(path_to_root) > 1:
            lines.append(f"知识路径：{' → '.join(n['name'] for n in path_to_root)}")

        # Siblings
        parent_id = cur["parent_id"]
        siblings = children_map.get(parent_id, [])
        siblings = [s for s in siblings if s["id"] != current_node_id]
        if siblings:
            parts = []
            for s in siblings:
                label = _mastery_label(s)
                parts.append(f"{s['name']}({label})")
            lines.append(f"同级知识点：{', '.join(parts)}")

        # Children
        children = children_map.get(current_node_id, [])
        if children:
            parts = []
            for c in children:
                label = _mastery_label(c)
                parts.append(f"{c['name']}({label})")
            lines.append(f"子知识点：{', '.join(parts)}")

    # ── B: Mastery Overview ──
    total = len(nodes)
    lines.append(f"\n📊 知识掌握概览：已掌握 {len(mastered)} 个 | 学习中 {len(learning)} 个 | 新 {len(new_nodes)} 个 | 总计 {total} 个节点")

    # ── C: All Mastered Nodes ──
    if mastered:
        lines.append(f"\n✅ 已掌握（{len(mastered)} 个）：")
        for n in mastered:
            domain = f" [领域：{n['domain_tag']}]" if n["domain_tag"] else ""
            lines.append(f"  - {n['name']}{domain}")

    # ── D: All Learning Nodes ──
    if learning:
        lines.append(f"\n📖 学习中（{len(learning)} 个）：")
        for n in learning:
            lines.append(f"  - {n['name']}")

    # ── E: All New Nodes ──
    if new_nodes:
        lines.append(f"\n🆕 新知识点（{len(new_nodes)} 个）：")
        for n in new_nodes:
            lines.append(f"  - {n['name']}")

    return "\n".join(lines)


def _mastery_label(node: dict) -> str:
    """Return a compact Chinese label for a node's mastery level."""
    score = node["mastery_score"]
    if score > 0.7:
        return "已掌握"
    elif score >= 0.3:
        return "学习中"
    return "新"
