"""
Static visual scaffolding shapes: tapered trunk + leader (_build_trunk),
ground points (_build_ground, seeds random at 42), root shapes (_build_roots),
and the apex-fill branch pairs (_apex_fill, which mutates all_branches in
place). _apex_fill and _build_roots call lsystem_iterate/interpret_lsystem
directly.
"""
import math
import random
from typing import List, Dict, Tuple

from lsystem_rules import lsystem_iterate
from lsystem_interpret import interpret_lsystem


def _build_trunk(
    trunk_base: Tuple[float, float],
    trunk_height: float,
    trunk_base_thickness: float,
    trunk_top_thickness: float,
    canvas_h: int,
) -> Tuple[List[Dict], float]:
    """Build tapered trunk + leader segments; returns (trunk_branches, leader_top_y)."""
    # --- Trunk: tapered ---
    trunk_branches: List[Dict] = []
    trunk_segments = 8
    for i in range(trunk_segments):
        t0 = i / trunk_segments
        t1 = (i + 1) / trunk_segments
        y0 = trunk_base[1] - trunk_height * t0
        y1 = trunk_base[1] - trunk_height * t1
        thickness = trunk_base_thickness - (trunk_base_thickness - trunk_top_thickness) * ((t0 + t1) / 2)
        trunk_branches.append({
            "start": [trunk_base[0], y0],
            "end": [trunk_base[0], y1],
            "control1": [trunk_base[0], y0 + (y1 - y0) * 0.33],
            "control2": [trunk_base[0], y0 + (y1 - y0) * 0.67],
            "thickness": thickness,
            "node_id": "__trunk__",
            "depth": -1,
        })

    # --- Trunk leader: continuation above the top branch layer ---
    # The trunk doesn't stop at the top branch — it keeps going up, getting thinner
    leader_length = canvas_h * 0.08
    leader_base_y = trunk_base[1] - trunk_height
    leader_top_y = leader_base_y - leader_length
    leader_base_thickness = trunk_top_thickness
    leader_top_thickness = leader_base_thickness * 0.4
    leader_segments = 4
    for i in range(leader_segments):
        t0 = i / leader_segments
        t1 = (i + 1) / leader_segments
        y0 = leader_base_y - leader_length * t0
        y1 = leader_base_y - leader_length * t1
        thickness = leader_base_thickness - (leader_base_thickness - leader_top_thickness) * ((t0 + t1) / 2)
        trunk_branches.append({
            "start": [trunk_base[0], y0],
            "end": [trunk_base[0], y1],
            "control1": [trunk_base[0], y0 + (y1 - y0) * 0.33],
            "control2": [trunk_base[0], y0 + (y1 - y0) * 0.67],
            "thickness": thickness,
            "node_id": "__trunk__",
            "depth": -1,
        })
    return trunk_branches, leader_top_y


def _build_ground(ground_y: float, canvas_w: int) -> List[List[float]]:
    """Build ground points along the base of the canvas."""
    random.seed(42)
    ground_points: List[List[float]] = []
    n_ground_pts = 40
    for i in range(n_ground_pts + 1):
        x = canvas_w * i / n_ground_pts
        bump = random.uniform(-3, 3)
        ground_points.append([x, ground_y + bump])
    return ground_points


def _build_roots(trunk_base: Tuple[float, float], total_nodes: int) -> List[Dict]:
    """Build root shapes descending from the trunk base."""
    n_roots = min(4, max(2, total_nodes // 5))
    roots_data: List[Dict] = []
    for i in range(n_roots):
        side = 1 if i % 2 == 0 else -1
        order = (i // 2) + 1
        angle = 90 - side * (15 + order * 12)
        length = 20 + order * 8
        end_x = trunk_base[0] + length * math.cos(math.radians(angle))
        end_y = trunk_base[1] + length * math.sin(math.radians(angle)) * 0.3
        thickness = max(2, 8 - order * 2)
        root_seed = hash(f"__root_{i}__") % (2**32)
        random.seed(root_seed)
        cp1_x = trunk_base[0] + (end_x - trunk_base[0]) * 0.33
        cp1_y = trunk_base[1] + (end_y - trunk_base[1]) * 0.33 + random.uniform(-2, 2)
        cp2_x = trunk_base[0] + (end_x - trunk_base[0]) * 0.67
        cp2_y = trunk_base[1] + (end_y - trunk_base[1]) * 0.67 + random.uniform(-2, 2)
        roots_data.append({
            "start": list(trunk_base),
            "end": [end_x, end_y],
            "control1": [cp1_x, cp1_y],
            "control2": [cp2_x, cp2_y],
            "thickness": thickness,
            "node_id": "__root__",
            "depth": -1,
        })
    return roots_data


def _apex_fill(
    all_branches: List[Dict],
    total_nodes: int,
    roots: List[Dict],
    base_branch_length: float,
    base_thickness: float,
    leader_top_y: float,
    canvas_w: int,
    canvas_h: int,
    trunk_base: Tuple[float, float],
    trunk_height: float,
) -> None:
    """Fill branches along the bare trunk leader; mutates all_branches in place."""
    # --- Apex fill: branches along the bare trunk leader ---
    # Find the actual highest canopy emergence point (where depth=0 branches start)
    canopy_start_ys = [b["start"][1] for b in all_branches if b.get("depth", -1) == 0]
    top_canopy_y = min(canopy_start_ys) if canopy_start_ys else trunk_base[1] - trunk_height * 0.80
    bare_top_y = leader_top_y  # top of the leader

    if top_canopy_y > bare_top_y:
        bare_length = top_canopy_y - bare_top_y
        # Place 3-5 pairs of branches along the bare section
        n_pairs = max(2, min(5, int(bare_length / 20)))
        fill_rule = "F[+F][-F]"
        fill_iterations = 2
        fill_lstring = lsystem_iterate("F", fill_rule, fill_iterations)

        for pair_idx in range(n_pairs):
            # Distribute evenly along the bare section, from bottom to top
            frac = (pair_idx + 1) / (n_pairs + 1)
            branch_y = top_canopy_y - bare_length * frac
            branch_pos = (canvas_w / 2, branch_y)

            # Branches get smaller and shorter toward the top
            size_decay = 1.0 - pair_idx * 0.15
            fill_len = base_branch_length * 0.30 * size_decay
            fill_thick = base_thickness * 0.35 * size_decay
            initial_len = fill_len * 0.5
            angle_delta = 30

            for side in [0, 1]:  # 0 = right, 1 = left
                seed = hash(f"__apex_{pair_idx}_{side}__") % (2**32)
                random.seed(seed)
                if side == 0:
                    base_angle = 55.0 + random.uniform(-10, 10)
                else:
                    base_angle = 125.0 + random.uniform(-10, 10)

                fill_branches = interpret_lsystem(
                    lstring=fill_lstring,
                    start_pos=branch_pos,
                    start_angle=base_angle,
                    initial_length=initial_len,
                    base_angle_delta=angle_delta,
                    node_id=f"__apex_{pair_idx}_{side}__",
                    depth=0,
                )

                # Check bounds
                margin = canvas_w * 0.03
                out_of_bounds = False
                for b in fill_branches:
                    for coord in [b["start"], b["end"]]:
                        if coord[0] < -margin or coord[0] > canvas_w + margin or coord[1] < -margin or coord[1] > canvas_h + margin:
                            out_of_bounds = True
                            break
                    if out_of_bounds:
                        break

                if not out_of_bounds and fill_branches:
                    for b in fill_branches:
                        b["thickness"] = max(1, fill_thick * (0.7 ** b["depth"]))
                        b["node_id"] = roots[0]["id"] if roots else "__unknown__"
                        b["descendants"] = total_nodes
                    all_branches.extend(fill_branches)
                    print(f"  apex pair {pair_idx} side {'R' if side == 0 else 'L'}: {len(fill_branches)} branches at y={branch_y:.0f}")
