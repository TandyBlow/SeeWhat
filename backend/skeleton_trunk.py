"""Deterministic trunk: tapered bezier segments along an S-curve (Step 4) plus the trunk leader (Step 10)."""
import math
import random
from typing import List, Dict, Tuple


# ---------------------------------------------------------------------------
# Step 4: Trunk
# ---------------------------------------------------------------------------

def _generate_trunk(
    canvas_w: int, canvas_h: int,
    ground_y: float,
    total_nodes: int,
    n_roots: int,
    user_uuid_seed: int,
    growth_multiplier: float = 1.0,
) -> Tuple[List[Dict], Tuple[float, float], Tuple[float, float], float, float]:
    """Returns (trunk_branches, trunk_base, trunk_top, trunk_base_thickness, trunk_top_thickness)"""

    rng = random.Random(user_uuid_seed)

    # Trunk height
    depth_factor = min(1.0, 0.4 + math.log2(max(total_nodes, 2)) * 0.08)
    node_factor = min(1.0, 0.5 + math.log2(max(total_nodes, 2)) * 0.07)
    trunk_height = canvas_h * 0.20 * depth_factor * node_factor + canvas_h * 0.15
    trunk_height *= growth_multiplier

    trunk_base = (canvas_w / 2, ground_y)
    trunk_top = (canvas_w / 2, ground_y - trunk_height)

    # Trunk thickness
    root_factor = min(1.0, 0.5 + n_roots * 0.1)
    node_thick_factor = min(1.0, 0.6 + math.log2(max(total_nodes, 2)) * 0.07)
    trunk_base_thickness = 10 + 15 * root_factor * node_thick_factor
    trunk_top_thickness = trunk_base_thickness * 0.4  # 2.5x ratio

    # S-curve: 3 control points (bottom, mid-offset, top)
    # Mid control point shifted by UUID seed
    mid_offset_x = (rng.random() - 0.5) * canvas_w * 0.04  # slight S bend
    mid_y = trunk_base[1] - trunk_height * 0.5

    # Generate 6 tapered segments along the S-curve
    trunk_branches: List[Dict] = []
    trunk_segments = 6
    for i in range(trunk_segments):
        t0 = i / trunk_segments
        t1 = (i + 1) / trunk_segments

        # Points on quadratic bezier: P = (1-t)^2*P0 + 2*(1-t)*t*P1 + t^2*P2
        p0 = _quad_bezier_point(
            trunk_base, (trunk_base[0] + mid_offset_x, mid_y), trunk_top, t0
        )
        p1 = _quad_bezier_point(
            trunk_base, (trunk_base[0] + mid_offset_x, mid_y), trunk_top, t1
        )
        t_mid = (t0 + t1) / 2
        pm = _quad_bezier_point(
            trunk_base, (trunk_base[0] + mid_offset_x, mid_y), trunk_top, t_mid
        )

        # Thickness at this segment (tapered)
        thickness_start = trunk_base_thickness - (trunk_base_thickness - trunk_top_thickness) * t0
        thickness_end = trunk_base_thickness - (trunk_base_thickness - trunk_top_thickness) * t1
        thickness = (thickness_start + thickness_end) / 2

        # Control points with small perpendicular perturbation
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        seg_len = math.hypot(dx, dy)
        if seg_len > 0:
            perp_angle = math.atan2(-dx, dy)
        else:
            perp_angle = 0

        rng.seed(user_uuid_seed + i)
        offset1 = rng.uniform(-2, 2)
        offset2 = rng.uniform(-2, 2)

        cp1 = (p0[0] + (pm[0] - p0[0]) * 0.67 + offset1 * math.cos(perp_angle),
               p0[1] + (pm[1] - p0[1]) * 0.67 + offset1 * math.sin(perp_angle))
        cp2 = (pm[0] + (p1[0] - pm[0]) * 0.33 + offset2 * math.cos(perp_angle),
               pm[1] + (p1[1] - pm[1]) * 0.33 + offset2 * math.sin(perp_angle))

        trunk_branches.append({
            "start": list(p0),
            "end": list(p1),
            "control1": list(cp1),
            "control2": list(cp2),
            "thickness": thickness,
            "node_id": "__trunk__",
            "depth": -1,
            "start_thickness": thickness_start,
            "end_thickness": thickness_end,
        })

    return trunk_branches, trunk_base, trunk_top, trunk_base_thickness, trunk_top_thickness


def _quad_bezier_point(p0, p1, p2, t):
    """Evaluate quadratic bezier at t."""
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return (x, y)


# ---------------------------------------------------------------------------
# Step 10: Trunk leader
# ---------------------------------------------------------------------------

def _generate_trunk_leader(
    trunk_top: Tuple[float, float],
    trunk_top_thickness: float,
    trunk_height: float,
    canvas_w: int,
    seed: int,
) -> List[Dict]:
    """Short continuation above the trunk top, getting very thin."""
    rng = random.Random(seed)
    leader_length = trunk_height * 0.12
    leader_top_y = trunk_top[1] - leader_length
    leader_top_thickness = trunk_top_thickness * 0.35

    segments = 3
    branches: List[Dict] = []
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        y0 = trunk_top[1] - leader_length * t0
        y1 = trunk_top[1] - leader_length * t1
        st = trunk_top_thickness - (trunk_top_thickness - leader_top_thickness) * t0
        et = trunk_top_thickness - (trunk_top_thickness - leader_top_thickness) * t1

        rng.seed(seed + i * 17)
        x_offset = rng.uniform(-1, 1)

        branches.append({
            "start": [trunk_top[0] + x_offset * t0, y0],
            "end": [trunk_top[0] + x_offset * t1, y1],
            "control1": [trunk_top[0] + x_offset * (t0 * 0.67 + t1 * 0.33), y0 + (y1 - y0) * 0.33],
            "control2": [trunk_top[0] + x_offset * (t0 * 0.33 + t1 * 0.67), y0 + (y1 - y0) * 0.67],
            "thickness": (st + et) / 2,
            "node_id": "__trunk__",
            "depth": -1,
            "start_thickness": st,
            "end_thickness": et,
        })

    return branches
