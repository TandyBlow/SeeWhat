"""Branch output generation: primary branches off the trunk (Step 4) and BranchNode-to-bezier conversion (Step 7)."""
import math
import random
from typing import List, Dict, Tuple, Optional
from skeleton_models import BranchNode, CrownOutline, Sector, ForkPoint


# ---------------------------------------------------------------------------
# Step 4: Primary branches
# ---------------------------------------------------------------------------

def _generate_primary_branches(
    trunk_base: Tuple[float, float],
    trunk_top: Tuple[float, float],
    trunk_height: float,
    trunk_base_thickness: float,
    trunk_top_thickness: float,
    root_stats: List[Dict],
    crown: CrownOutline,
    sectors: List[Sector],
    seed: int,
) -> Tuple[List[Dict], List[BranchNode], List[ForkPoint], float]:
    """
    Returns (primary_branches, initial_sc_nodes, fork_points, trunk_base_thickness_at_fork)
    """
    rng = random.Random(seed)

    primary_branches: List[Dict] = []
    initial_nodes: List[BranchNode] = []
    fork_points: List[ForkPoint] = []

    n_branches = len(root_stats)
    if n_branches == 0:
        return primary_branches, initial_nodes, fork_points, trunk_top_thickness

    # Fork heights distributed 60%-85% up trunk
    for i, rs in enumerate(root_stats):
        if n_branches == 1:
            fork_frac = 0.72
        else:
            fork_frac = 0.60 + (0.25 * i / (n_branches - 1))

        fork_y = trunk_base[1] - trunk_height * fork_frac

        # Trunk thickness at fork point (linearly interpolated)
        trunk_thickness_at_fork = trunk_base_thickness + (trunk_top_thickness - trunk_base_thickness) * fork_frac

        # Direction toward sector center
        sector = sectors[i] if i < len(sectors) else sectors[0]
        target_x = crown.center_x + crown.semi_axis_x * 0.5 * math.cos(sector.angle_center)
        target_y = crown.center_y + crown.semi_axis_y * 0.3 * math.sin(sector.angle_center)

        fork_pos = (trunk_base[0], fork_y)

        # Primary branch: bezier from fork to a point toward the sector
        branch_length = min(crown.semi_axis_x, crown.semi_axis_y) * 0.6
        rng_local = random.Random(seed + i * 137)
        end_x = fork_pos[0] + (target_x - fork_pos[0]) * 0.5
        end_y = fork_pos[1] + (target_y - fork_pos[1]) * 0.5

        # Control points
        cp1_x = fork_pos[0] + (end_x - fork_pos[0]) * 0.33 + rng_local.uniform(-5, 5)
        cp1_y = fork_pos[1] + (end_y - fork_pos[1]) * 0.33
        cp2_x = fork_pos[0] + (end_x - fork_pos[0]) * 0.67 + rng_local.uniform(-5, 5)
        cp2_y = fork_pos[1] + (end_y - fork_pos[1]) * 0.67

        # Thickness: da Vinci pipe model will refine later, initial estimate
        branch_thickness = trunk_thickness_at_fork * 0.5

        primary_branches.append({
            "start": list(fork_pos),
            "end": [end_x, end_y],
            "control1": [cp1_x, cp1_y],
            "control2": [cp2_x, cp2_y],
            "thickness": branch_thickness,
            "node_id": rs["id"],
            "depth": 0,
            "start_thickness": trunk_thickness_at_fork * 0.6,
            "end_thickness": trunk_thickness_at_fork * 0.25,
            "is_terminal": False,
        })

        # Fork point sphere
        fork_radius = trunk_thickness_at_fork * 0.35
        fork_points.append(ForkPoint(
            position=fork_pos,
            radius=fork_radius,
            is_primary=True,
            root_id=rs["id"],
        ))

        # Space Colonization starting node at branch tip
        initial_nodes.append(BranchNode(
            position=(end_x, end_y),
            parent_index=None,
            root_id=rs["id"],
            depth=1,
            thickness=0,
        ))

    return primary_branches, initial_nodes, fork_points, trunk_top_thickness


# ---------------------------------------------------------------------------
# Step 7: Convert BranchNodes to Bezier Branches
# ---------------------------------------------------------------------------

def _nodes_to_bezier_branches(
    all_nodes: List[BranchNode],
    seed: int,
    mastery_by_root: Dict[str, float] | None = None,
) -> List[Dict]:
    branches: List[Dict] = []
    mastery_lookup = mastery_by_root or {}

    for i, node in enumerate(all_nodes):
        if node.parent_index is None:
            continue

        parent = all_nodes[node.parent_index]
        start = parent.position
        end = node.position

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        seg_len = math.hypot(dx, dy)
        if seg_len < 1:
            continue

        # Perpendicular perturbation for control points
        rng = random.Random(seed + i * 7)
        if seg_len > 0:
            perp_angle = math.atan2(-dx, dy)
        else:
            perp_angle = 0

        max_offset = seg_len * 0.25
        offset1 = rng.uniform(-max_offset, max_offset)
        offset2 = rng.uniform(-max_offset, max_offset)

        cp1_x = start[0] + dx * 0.33 + offset1 * math.cos(perp_angle)
        cp1_y = start[1] + dy * 0.33 + offset1 * math.sin(perp_angle)
        cp2_x = start[0] + dx * 0.67 + offset2 * math.cos(perp_angle)
        cp2_y = start[1] + dy * 0.67 + offset2 * math.sin(perp_angle)

        start_thickness = parent.thickness if parent.thickness > 0 else 2.0
        end_thickness = node.thickness if node.thickness > 0 else 1.0
        # Taper: end_thickness should be 40% of start_thickness minimum
        end_thickness = min(end_thickness, start_thickness * 0.95)
        end_thickness = max(end_thickness, start_thickness * 0.3)

        is_terminal = len(node.children_indices) == 0
        mastery = mastery_lookup.get(node.root_id, 0.0)

        branches.append({
            "start": list(start),
            "end": list(end),
            "control1": [cp1_x, cp1_y],
            "control2": [cp2_x, cp2_y],
            "thickness": (start_thickness + end_thickness) / 2,
            "node_id": node.root_id,
            "depth": node.depth,
            "start_thickness": start_thickness,
            "end_thickness": end_thickness,
            "is_terminal": is_terminal,
            "descendants": 0,  # will be filled later
            "mastery_score": round(mastery, 4),
        })

    # Fill descendants: count terminal branches with same root_id
    root_terminal_counts: Dict[str, int] = {}
    for b in branches:
        if b["is_terminal"]:
            root_terminal_counts[b["node_id"]] = root_terminal_counts.get(b["node_id"], 0) + 1

    for b in branches:
        b["descendants"] = root_terminal_counts.get(b["node_id"], 0)

    return branches
