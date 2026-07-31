"""
Interprets an L-system string into branch coordinates (start/end/control
points, thickness, depth). Deterministic via local random.seed(seed +
branch_index). Used by the canopy and apex builders.
"""
import math
import random
from typing import List, Dict, Tuple


def interpret_lsystem(
    lstring: str,
    start_pos: Tuple[float, float],
    start_angle: float,
    initial_length: float,
    base_angle_delta: float,
    node_id: str,
    depth: int
) -> List[Dict]:
    """
    Interpret L-system string into branch coordinates.

    Length decays at branch points `[`, not per segment `F`.
    This prevents exponential decay on consecutive F's (e.g. rule prefix "FF").
    """
    MAX_BRANCHES = 500

    stack = []
    pos = start_pos
    angle = start_angle
    length = initial_length
    branches: List[Dict] = []
    branch_index = 0

    seed = hash(node_id) % (2**32)

    for char in lstring:
        if len(branches) >= MAX_BRANCHES:
            break

        if char == 'F':
            new_x = pos[0] + length * math.cos(math.radians(angle))
            new_y = pos[1] - length * math.sin(math.radians(angle))
            new_pos = (new_x, new_y)

            dx = new_x - pos[0]
            dy = new_y - pos[1]
            seg_len = math.hypot(dx, dy)

            # Skip zero-length or near-zero branches
            if seg_len < 1:
                pos = new_pos
                branch_index += 1
                continue

            random.seed(seed + branch_index)

            max_offset = seg_len * 0.30

            t1 = 0.33
            cp1_x = pos[0] + dx * t1
            cp1_y = pos[1] + dy * t1
            perp_angle = angle + 90
            offset1 = random.uniform(-length * 0.15, length * 0.15)
            offset1 = max(-max_offset, min(max_offset, offset1))
            cp1_x += offset1 * math.cos(math.radians(perp_angle))
            cp1_y -= offset1 * math.sin(math.radians(perp_angle))

            t2 = 0.67
            cp2_x = pos[0] + dx * t2
            cp2_y = pos[1] + dy * t2
            offset2 = random.uniform(-length * 0.15, length * 0.15)
            offset2 = max(-max_offset, min(max_offset, offset2))
            cp2_x += offset2 * math.cos(math.radians(perp_angle))
            cp2_y -= offset2 * math.sin(math.radians(perp_angle))

            # Thickness based on stack depth (branch level)
            branch_depth = len(stack)
            thickness = max(1, 8 - branch_depth)

            branches.append({
                "start": list(pos),
                "end": list(new_pos),
                "control1": [cp1_x, cp1_y],
                "control2": [cp2_x, cp2_y],
                "thickness": thickness,
                "node_id": node_id,
                "depth": branch_depth,
            })

            pos = new_pos
            # NO length decay here — same-level segments keep their length

        elif char == '+':
            random.seed(seed + branch_index)
            perturbation = random.uniform(-5, 5)
            angle -= (base_angle_delta + perturbation)
            branch_index += 1

        elif char == '-':
            random.seed(seed + branch_index)
            perturbation = random.uniform(-5, 5)
            angle += (base_angle_delta + perturbation)
            branch_index += 1

        elif char == '[':
            # Save current state, then reduce length for the new branch
            stack.append((pos, angle, length))
            length *= 0.7

        elif char == ']':
            # Restore state (length is restored to pre-branch value)
            if stack:
                pos, angle, length = stack.pop()

    return branches
