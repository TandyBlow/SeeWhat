"""
Multi-layer canopy branch generation (_build_canopy): layer count driven by
total_nodes, symmetric base angles, per-layer branch generation through
interpret_lsystem with retry/clamping toward 90deg, and crown-layer geometry.
Requires base_thickness/base_branch_length passed in from the orchestrator.
"""
import math
import random
from typing import List, Dict, Tuple

from lsystem_rules import lsystem_iterate
from lsystem_interpret import interpret_lsystem


def _build_canopy(
    total_nodes: int,
    roots: List[Dict],
    trunk_base: Tuple[float, float],
    trunk_height: float,
    canvas_w: int,
    canvas_h: int,
    base_thickness: float,
    base_branch_length: float,
) -> Tuple[List[Dict], List[Dict]]:
    """Build multi-layer canopy branches; returns (all_branches, crown_layers)."""
    all_branches: List[Dict] = []
    crown_layers: List[Dict] = []

    # Layer count and branches per layer driven by total_nodes only
    if total_nodes <= 3:
        n_layers = 1
        branches_per_layer = [2]
    elif total_nodes <= 8:
        n_layers = 2
        branches_per_layer = [2, 2]
    elif total_nodes <= 20:
        n_layers = 2
        branches_per_layer = [3, 3]
    elif total_nodes <= 40:
        n_layers = 3
        branches_per_layer = [2, 3, 3]
    else:
        n_layers = 3
        branches_per_layer = [3, 4, 4]

    for layer_idx in range(n_layers):
        n_in_layer = branches_per_layer[layer_idx]

        # Layer emergence point along the trunk
        # Layer 0 (lowest) → 35% up trunk, layer N-1 (highest) → 80% up trunk
        layer_frac = (layer_idx + 0.5) / n_layers
        trunk_frac = 0.35 + layer_frac * 0.45
        emergence_y = trunk_base[1] - trunk_height * trunk_frac
        emergence_pos = (canvas_w / 2, emergence_y)

        # Upper layers get shorter, thinner branches
        layer_length = base_branch_length * (1.0 - layer_idx * 0.20)
        layer_thickness = base_thickness * (1.0 - layer_idx * 0.15)

        # Symmetric base angles: lower layers spread more, upper layers steeper
        # layer_idx 0 (bottom): ~40°/140°, layer N-1 (top): ~65°/115°
        right_count = (n_in_layer + 1) // 2
        left_count = n_in_layer // 2
        base_right = 50.0 + layer_idx * 10.0  # 50, 60, 70
        base_left = 130.0 - layer_idx * 10.0   # 130, 120, 110
        layer_angles = []
        for i in range(n_in_layer):
            is_right = i % 2 == 0
            if is_right:
                idx = i // 2
                base = base_right + idx * (8.0 / max(right_count, 1))
            else:
                idx = i // 2
                base = base_left - idx * (8.0 / max(left_count, 1))
            layer_angles.append(base)

        iterations = 2
        rule = "F[+F][-F]"

        lstring = lsystem_iterate("F", rule, iterations)
        initial_length = layer_length * 0.5
        angle_delta = max(15, 25 - iterations * 2)

        for li in range(n_in_layer):
            base_angle = layer_angles[li]
            seed = hash(f"branch_L{layer_idx}_{li}") % (2**32)

            random.seed(seed)
            # Random perturbation: angle ±8°, length ±20%
            angle_perturbation = random.uniform(-8, 8)
            length_multiplier = 0.8 + random.random() * 0.4  # 0.8 to 1.2
            start_angle = base_angle + angle_perturbation
            branch_initial_length = initial_length * length_multiplier

            print(f"  layer {layer_idx} branch {li}: emergence={trunk_frac:.2f} angle={base_angle:.1f}°+{angle_perturbation:.1f}° len_factor={length_multiplier:.2f} iterations={iterations}")

            branches: List[Dict] = []
            max_retries = 5
            out_of_bounds = False
            for attempt in range(max_retries):
                candidate = interpret_lsystem(
                    lstring=lstring,
                    start_pos=emergence_pos,
                    start_angle=start_angle,
                    initial_length=branch_initial_length,
                    base_angle_delta=angle_delta,
                    node_id=f"__layer{layer_idx}_branch{li}__",
                    depth=0,
                )

                out_of_bounds = False
                margin = canvas_w * 0.03
                for b in candidate:
                    for coord in [b["start"], b["end"]]:
                        if coord[0] < -margin or coord[0] > canvas_w + margin or coord[1] < -margin or coord[1] > canvas_h + margin:
                            out_of_bounds = True
                            break
                    if out_of_bounds:
                        break

                if not out_of_bounds:
                    branches = candidate
                    break

                print(f"    attempt {attempt+1} out-of-bounds, clamping toward 90°")
                start_angle = 90 + (start_angle - 90) * 0.5

            if out_of_bounds:
                print(f"    WARNING: branch {li} still OOB after {max_retries} retries, discarding")
                continue

            for b in branches:
                b["thickness"] = max(1, layer_thickness * (0.7 ** b["depth"]))
                b["node_id"] = roots[0]["id"] if roots else "__unknown__"
                b["descendants"] = total_nodes

            all_branches.extend(branches)

        # Compute crown layer geometry
        layer_xs = [b["end"][0] for b in all_branches if b.get("depth", -1) >= 0]
        layer_ys = [b["end"][1] for b in all_branches if b.get("depth", -1) >= 0]

        if layer_xs and layer_ys:
            min_x, max_x = min(layer_xs), max(layer_xs)
            min_y, max_y = min(layer_ys), max(layer_ys)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            pad_x = (max_x - min_x) * 0.15 + canvas_w * 0.03
            pad_y = (max_y - min_y) * 0.15 + canvas_h * 0.02
            crown_layers.append({
                "center": [cx, cy],
                "width": (max_x - min_x) / 2 + pad_x,
                "height": (max_y - min_y) / 2 + pad_y,
            })

    return all_branches, crown_layers
