"""Orchestrator: generate_tree_skeleton() wires all generator steps into the SkeletonData v2 dict."""
from typing import List, Dict, Tuple
from skeleton_stats import _compute_tree_stats
from skeleton_crown import _generate_crown_outline, _distribute_attractors
from skeleton_trunk import _generate_trunk, _generate_trunk_leader
from skeleton_branches import _generate_primary_branches, _nodes_to_bezier_branches
from skeleton_sc import _space_colonization
from skeleton_thickness import _compute_thicknesses
from skeleton_roots import _generate_roots, _generate_ground


def _uuid_seed(node_ids: List[str]) -> int:
    if not node_ids:
        return 42
    return hash(node_ids[0]) % (2 ** 32)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_tree_skeleton(
    tree_data: List[Dict],
    canvas_w: int = 512,
    canvas_h: int = 512,
) -> Dict:
    """
    Generate tree skeleton using Space Colonization algorithm.

    Input: list of node dicts with {id, name, depth, parent_id, child_count, mastery_score}
    Output: SkeletonData v2 dict
    """
    canvas_w = 512
    canvas_h = 512

    if not tree_data:
        return {
            "branches": [],
            "canvas_size": [canvas_w, canvas_h],
            "trunk": None,
            "ground": None,
            "roots": [],
            "crown_layers": [],
            "version": 2,
            "growth": None,
        }

    stats = _compute_tree_stats(tree_data)
    if stats is None:
        return {
            "branches": [],
            "canvas_size": [canvas_w, canvas_h],
            "trunk": None,
            "ground": None,
            "roots": [],
            "crown_layers": [],
            "version": 2,
            "growth": None,
        }

    (children_map, parent_map, root_stats,
     total_nodes, global_max_depth,
     width_depth_ratio, max_subtree_ratio, health) = stats

    n_roots = len(root_stats)
    seed = _uuid_seed([rs["id"] for rs in root_stats])
    growth_multiplier = health["growth_multiplier"]

    # --- Layout constants ---
    ground_y = canvas_h * 0.88

    # --- Step 1: Trunk ---
    trunk_result = _generate_trunk(canvas_w, canvas_h, ground_y, total_nodes, n_roots, seed, growth_multiplier)
    trunk_branches, trunk_base, trunk_top, trunk_base_thickness, trunk_top_thickness = trunk_result

    # --- Step 2: Crown outline ---
    crown = _generate_crown_outline(
        canvas_w, canvas_h, total_nodes,
        width_depth_ratio, max_subtree_ratio,
        trunk_top, seed + 1, growth_multiplier,
    )

    # --- Step 3: Attractors ---
    sectors = _distribute_attractors(crown, root_stats, total_nodes, seed + 2, growth_multiplier)

    # --- Step 4: Primary branches ---
    primary_result = _generate_primary_branches(
        trunk_base, trunk_top,
        trunk_base[1] - trunk_top[1],  # trunk_height
        trunk_base_thickness, trunk_top_thickness,
        root_stats, crown, sectors, seed + 3,
    )
    primary_branches, initial_sc_nodes, fork_points, _ = primary_result

    # --- Step 5: Space Colonization ---
    sc_nodes = _space_colonization(
        initial_sc_nodes, sectors, crown, seed + 4,
    )

    # --- Step 6: da Vinci thickness ---
    _compute_thicknesses(sc_nodes, trunk_base_thickness, trunk_top_thickness)

    # Build mastery lookup by root id
    mastery_by_root = {rs["id"]: rs["mastery_score"] for rs in root_stats}

    # --- Step 7: Convert to Bezier branches ---
    sc_branches = _nodes_to_bezier_branches(sc_nodes, seed + 5, mastery_by_root)

    # --- Trunk leader ---
    leader_branches = _generate_trunk_leader(trunk_top, trunk_top_thickness, trunk_base[1] - trunk_top[1], canvas_w, seed + 6)
    trunk_branches.extend(leader_branches)

    # --- Step 8: Roots ---
    root_branches, root_tip_positions = _generate_roots(
        trunk_base, trunk_base_thickness, total_nodes, seed + 7,
    )

    # --- Step 9: Ground ---
    ground_points = _generate_ground(canvas_w, canvas_h, ground_y, root_tip_positions, seed + 8)

    # --- Root bulges ---
    root_bulges = [
        {"position": list(pos), "radius": trunk_base_thickness * 0.5}
        for pos in root_tip_positions
    ]

    # --- Combine all branches ---
    all_branches = primary_branches + sc_branches

    print(f"[generate_tree_skeleton] roots={n_roots}, total_nodes={total_nodes}, "
          f"sc_nodes={len(sc_nodes)}, branches={len(all_branches)}, "
          f"crown=({crown.semi_axis_x:.0f}x{crown.semi_axis_y:.0f} n={crown.superellipse_n:.1f})"
          f" health={health}")

    return {
        "branches": all_branches,
        "canvas_size": [canvas_w, canvas_h],
        "trunk": trunk_branches,
        "ground": ground_points,
        "roots": root_branches,
        "crown_layers": [],  # v1 compat
        "version": 2,
        "fork_points": [
            {"position": list(fp.position), "radius": fp.radius, "is_primary": fp.is_primary, "root_id": fp.root_id}
            for fp in fork_points
        ],
        "crown_outline": {
            "center": [crown.center_x, crown.center_y],
            "semi_axis_x": crown.semi_axis_x,
            "semi_axis_y": crown.semi_axis_y,
            "eccentricity_x": crown.eccentricity_x,
            "superellipse_n": crown.superellipse_n,
            "points": [list(p) for p in crown.points],
        },
        "root_bulges": root_bulges,
        "growth": health,
    }
