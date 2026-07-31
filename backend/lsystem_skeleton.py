"""
Orchestrator module for L-system tree skeleton generation. Computes tree
statistics and drives the trunk/ground/roots/canopy/apex builders in exact
original order (preserving process-global random.seed call order).
"""
import math
from typing import List, Dict, Tuple

from lsystem_trunk import _build_trunk, _build_ground, _build_roots, _apex_fill
from lsystem_canopy import _build_canopy


def _count_descendants(node_id: str, children_map: Dict[str, List[str]]) -> int:
    """Count total descendants of a node (not including itself)."""
    count = 0
    for cid in children_map.get(node_id, []):
        count += 1 + _count_descendants(cid, children_map)
    return count


def _max_depth(node_id: str, children_map: Dict[str, List[str]], current: int = 0) -> int:
    """Get max depth below a node (0 if leaf)."""
    children = children_map.get(node_id, [])
    if not children:
        return current
    return max(_max_depth(cid, children_map, current + 1) for cid in children)


def _build_tree_index(tree_data: List[Dict]) -> Dict[str, List[str]]:
    """Build children adjacency map from tree_data."""
    children_map: Dict[str, List[str]] = {}
    for node in tree_data:
        pid = node.get("parent_id")
        if pid:
            children_map.setdefault(pid, []).append(node["id"])
    return children_map


def _compute_root_stats(roots: List[Dict], children_map: Dict[str, List[str]]) -> Tuple[List[Dict], int]:
    """Compute per-root descendant/depth statistics; returns (root_stats, global_max_depth)."""
    root_stats: List[Dict] = []
    global_max_depth = 0
    for root in roots:
        desc = _count_descendants(root["id"], children_map)
        depth = _max_depth(root["id"], children_map)
        global_max_depth = max(global_max_depth, depth)
        root_stats.append({
            "id": root["id"],
            "name": root["name"],
            "descendants": desc,
            "depth": depth,
        })
    return root_stats, global_max_depth


def _compute_trunk_metrics(
    canvas_w: int,
    canvas_h: int,
    n_roots_actual: int,
    total_nodes: int,
    global_max_depth: int,
) -> Tuple[float, Tuple[float, float], float, float, float]:
    """Compute canvas/trunk layout constants."""
    ground_y = canvas_h * 0.88
    trunk_base = (canvas_w / 2, ground_y)

    # Trunk height: scales with max_depth and total_nodes
    depth_factor = min(1.0, 0.4 + global_max_depth * 0.08)
    node_factor = min(1.0, 0.5 + math.log2(max(total_nodes, 2)) * 0.08)
    trunk_height = canvas_h * 0.20 * depth_factor * node_factor + canvas_h * 0.15

    # Trunk thickness: scales with root count and total_nodes
    root_factor = min(1.0, 0.5 + n_roots_actual * 0.1)
    node_thick_factor = min(1.0, 0.6 + math.log2(max(total_nodes, 2)) * 0.07)
    trunk_base_thickness = 10 + 15 * root_factor * node_thick_factor
    trunk_top_thickness = trunk_base_thickness * 0.45

    return ground_y, trunk_base, trunk_height, trunk_base_thickness, trunk_top_thickness


def generate_lsystem_skeleton(tree_data: List[Dict], _canvas_w: int = 512, _canvas_h: int = 512) -> Dict:
    """
    Generate visually appealing tree skeleton driven by data statistics.

    Design logic:
    - Root node count → number of main branches from trunk top
    - Each root's descendant count → that branch's thickness + L-system iterations
    - Max tree depth → overall tree height
    - Branches carry root's node_id (clickable to identify which knowledge root)
    """
    # Fixed 512x512 — tree structure depends on data, not viewport size
    canvas_w = 512
    canvas_h = 512

    if not tree_data:
        return {"branches": [], "canvas_size": [canvas_w, canvas_h], "trunk": None, "ground": None, "roots": [], "crown_layers": []}

    # Build adjacency from tree_data
    children_map = _build_tree_index(tree_data)

    # Find roots
    roots = [n for n in tree_data if n["parent_id"] is None]
    if not roots:
        roots = [n for n in tree_data if n["depth"] == 0]
    if not roots:
        return {"branches": [], "canvas_size": [canvas_w, canvas_h], "trunk": None, "ground": None, "roots": [], "crown_layers": []}

    # --- Compute statistics per root ---
    root_stats, global_max_depth = _compute_root_stats(roots, children_map)

    total_nodes = len(tree_data)

    print(f"[generate_lsystem_skeleton] roots={len(roots)}, total_nodes={total_nodes}, max_depth={global_max_depth}")
    for rs in root_stats:
        print(f"  root {rs['name']!r}: descendants={rs['descendants']}, depth={rs['depth']}")

    # --- Canvas & layout ---
    n_roots_actual = len(roots)
    ground_y, trunk_base, trunk_height, trunk_base_thickness, trunk_top_thickness = _compute_trunk_metrics(canvas_w, canvas_h, n_roots_actual, total_nodes, global_max_depth)

    # --- Trunk: tapered ---
    trunk_branches, leader_top_y = _build_trunk(trunk_base, trunk_height, trunk_base_thickness, trunk_top_thickness, canvas_h)

    # --- Ground ---
    ground_points = _build_ground(ground_y, canvas_w)

    # --- Roots ---
    roots_data = _build_roots(trunk_base, total_nodes)

    # --- Multi-layer canopy ---
    base_thickness = 4 + min(8, total_nodes * 0.15)
    # Base branch length for the lowest layer; upper layers get shorter
    base_branch_length = canvas_w * min(0.18, 0.08 + math.log2(max(total_nodes, 2)) * 0.02)

    all_branches, crown_layers = _build_canopy(total_nodes, roots, trunk_base, trunk_height, canvas_w, canvas_h, base_thickness, base_branch_length)

    print(f"[generate_lsystem_skeleton] generated {len(all_branches)} branches from {total_nodes} nodes ({n_roots_actual} roots)")

    # --- Apex fill: branches along the bare trunk leader ---
    _apex_fill(all_branches, total_nodes, roots, base_branch_length, base_thickness, leader_top_y, canvas_w, canvas_h, trunk_base, trunk_height)

    return {
        "branches": all_branches,
        "canvas_size": [canvas_w, canvas_h],
        "trunk": trunk_branches,
        "ground": ground_points,
        "roots": roots_data,
        "crown_layers": crown_layers,
    }
