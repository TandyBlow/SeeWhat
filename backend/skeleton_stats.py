"""Tree-structure statistics computed from the raw node list (Step 1)."""
import math
from typing import Dict, List, Optional


def _count_descendants(node_id: str, children_map: Dict[str, List[str]]) -> int:
    count = 0
    for cid in children_map.get(node_id, []):
        count += 1 + _count_descendants(cid, children_map)
    return count


def _max_depth(node_id: str, children_map: Dict[str, List[str]], current: int = 0) -> int:
    children = children_map.get(node_id, [])
    if not children:
        return current
    return max(_max_depth(cid, children_map, current + 1) for cid in children)


# ---------------------------------------------------------------------------
# Step 1: Compute tree statistics
# ---------------------------------------------------------------------------

def _compute_tree_stats(tree_data: List[Dict]):
    parent_map: Dict[str, Optional[str]] = {}
    children_map: Dict[str, List[str]] = {}
    node_by_id: Dict[str, Dict] = {n["id"]: n for n in tree_data}

    for node in tree_data:
        pid = node.get("parent_id")
        parent_map[node["id"]] = pid
        if pid:
            children_map.setdefault(pid, []).append(node["id"])

    roots = [n for n in tree_data if n.get("parent_id") is None]
    if not roots:
        roots = [n for n in tree_data if n.get("depth") == 0]
    if not roots:
        return None  # empty tree

    root_stats: List[Dict] = []
    global_max_depth = 0
    total_stability = 0.0
    total_mastery = 0.0
    reviewed_count = 0
    for root in roots:
        desc = _count_descendants(root["id"], children_map)
        depth = _max_depth(root["id"], children_map)
        global_max_depth = max(global_max_depth, depth)
        stability = root.get("stability", 0.0)
        mastery = root.get("mastery_score", 0.0)
        review_count = root.get("review_count", 0)
        total_stability += stability
        total_mastery += mastery
        if review_count > 0:
            reviewed_count += 1
        root_stats.append({
            "id": root["id"],
            "name": root["name"],
            "descendants": desc,
            "depth": depth,
            "subtree_size": desc + 1,  # includes self
            "mastery_score": mastery,
            "stability": stability,
            "difficulty": root.get("difficulty", 0.3),
            "review_count": review_count,
            "review_state": root.get("review_state", "new"),
        })

    total_nodes = len(tree_data)
    n_roots = len(roots)
    width_depth_ratio = n_roots / max(global_max_depth, 1)
    width_depth_ratio = max(0.1, min(10.0, width_depth_ratio))

    max_subtree = max(rs["subtree_size"] for rs in root_stats)
    max_subtree_ratio = max_subtree / total_nodes if total_nodes > 0 else 0

    # Aggregate FSRS health metrics
    avg_stability = round(total_stability / n_roots, 2) if n_roots > 0 else 0.0
    avg_mastery = round(total_mastery / n_roots, 4) if n_roots > 0 else 0.0
    review_coverage = round(reviewed_count / n_roots, 4) if n_roots > 0 else 0.0

    # Growth multiplier: uniform scalar applied to all tree dimensions.
    # Reflects "developmental maturity" independent of structure.
    # stability_norm 0→0, ~5→0.52, ~30→0.99
    stability_norm = min(1.0, math.log(1 + avg_stability) / math.log(31)) if avg_stability > 0 else 0.0
    maturity = 0.3 * review_coverage + 0.7 * stability_norm
    growth_multiplier = round(0.3 + 2.2 * maturity, 4)  # 0.3 (seedling) → 2.5 (fully mature)

    health = {
        "avg_stability": avg_stability,
        "avg_mastery": avg_mastery,
        "review_coverage": review_coverage,
        "total_nodes": total_nodes,
        "reviewed_nodes": reviewed_count,
        "growth_multiplier": growth_multiplier,
    }

    return (
        children_map, parent_map, root_stats,
        total_nodes, global_max_depth,
        width_depth_ratio, max_subtree_ratio, health,
    )
