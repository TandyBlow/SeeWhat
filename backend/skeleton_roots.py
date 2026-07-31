"""Ground-level generation (Steps 8-9): root bezier branches and the jittered ground line."""
import math
import random
from typing import List, Dict, Tuple


# ---------------------------------------------------------------------------
# Step 8: Root generation
# ---------------------------------------------------------------------------

def _generate_roots(
    trunk_base: Tuple[float, float],
    trunk_base_thickness: float,
    total_nodes: int,
    user_uuid_seed: int,
) -> Tuple[List[Dict], List[Tuple[float, float]]]:
    rng = random.Random(user_uuid_seed)

    if total_nodes < 30:
        n_roots = 3
    elif total_nodes < 100:
        n_roots = 4
    else:
        n_roots = 5

    root_branches: List[Dict] = []
    root_tip_positions: List[Tuple[float, float]] = []

    # Angular offset seeded by UUID
    base_angle_offset = rng.uniform(0, 2 * math.pi / n_roots)

    for i in range(n_roots):
        angle = base_angle_offset + (2 * math.pi * i / n_roots)
        # Add asymmetry
        angle += rng.uniform(-0.3, 0.3)

        # Root extends outward then downward
        horizontal_dist = 15 + trunk_base_thickness * 0.8
        vertical_drop = 12 + trunk_base_thickness * 0.4

        end_x = trunk_base[0] + horizontal_dist * math.cos(angle)
        end_y = trunk_base[1] + vertical_drop  # below ground

        # Bezier: horizontal outward first, then curve downward
        rng.seed(user_uuid_seed + i * 31)
        cp1_x = trunk_base[0] + horizontal_dist * 0.6 * math.cos(angle) + rng.uniform(-2, 2)
        cp1_y = trunk_base[1] + vertical_drop * 0.1
        cp2_x = end_x + rng.uniform(-2, 2)
        cp2_y = trunk_base[1] + vertical_drop * 0.6

        start_thickness = trunk_base_thickness * 0.6
        end_thickness = trunk_base_thickness * 0.1

        root_branches.append({
            "start": list(trunk_base),
            "end": [end_x, end_y],
            "control1": [cp1_x, cp1_y],
            "control2": [cp2_x, cp2_y],
            "thickness": (start_thickness + end_thickness) / 2,
            "node_id": "__root__",
            "depth": -1,
            "start_thickness": start_thickness,
            "end_thickness": end_thickness,
        })

        root_tip_positions.append((end_x, end_y))

    return root_branches, root_tip_positions


# ---------------------------------------------------------------------------
# Step 9: Ground generation
# ---------------------------------------------------------------------------

def _generate_ground(
    canvas_w: int, canvas_h: int,
    ground_y: float,
    root_tip_positions: List[Tuple[float, float]],
    seed: int,
) -> List[List[float]]:
    rng = random.Random(seed)
    ground_points: List[List[float]] = []
    n_ground_pts = 40

    for i in range(n_ground_pts + 1):
        x = canvas_w * i / n_ground_pts
        bump = rng.uniform(-3, 3)
        ground_points.append([x, ground_y + bump])

    return ground_points
