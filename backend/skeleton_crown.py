"""Crown generation: superellipse outline (Step 2) and sector-based attractor distribution (Step 3)."""
import math
import random
from typing import List, Dict, Tuple
from skeleton_models import CrownOutline, Sector
from skeleton_geometry import _sample_superellipse, _point_in_superellipse


# ---------------------------------------------------------------------------
# Step 2: Crown outline
# ---------------------------------------------------------------------------

def _generate_crown_outline(
    canvas_w: int, canvas_h: int,
    total_nodes: int,
    width_depth_ratio: float,
    max_subtree_ratio: float,
    trunk_top: Tuple[float, float],
    seed: int,
    growth_multiplier: float = 1.0,
) -> CrownOutline:
    rng = random.Random(seed)

    # Superellipse exponent n: wide trees -> higher n (flatter top), deep trees -> lower n
    if width_depth_ratio > 1.2:
        n = 2.5 + min(1.0, (width_depth_ratio - 1.2) * 1.25)  # 2.5 ~ 3.5
    elif width_depth_ratio < 0.8:
        n = 2.0
    else:
        n = 2.0 + (width_depth_ratio - 0.8) * (0.5 / 0.4)  # 2.0 ~ 2.5

    # Area = k * log(total_nodes + 1), mapped to pixel area
    # Target area in pixels
    target_area = canvas_w * canvas_h * 0.25 * math.log(max(total_nodes, 2) + 1) / math.log(50)

    # Aspect ratio from width_depth_ratio
    if width_depth_ratio > 1.2:
        aspect = min(2.0, width_depth_ratio)  # wider
    elif width_depth_ratio < 0.8:
        aspect = max(0.5, width_depth_ratio)  # taller
    else:
        aspect = 1.0

    # semi_axis_y * semi_axis_x * (gamma(1+1/n)^2 / gamma(1+2/n)) ≈ area for superellipse
    # Simplification: approximate area as pi*a*b (close enough for n near 2)
    area_factor = math.pi
    semi_axis_y = math.sqrt(target_area / (area_factor * aspect))
    semi_axis_x = semi_axis_y * aspect

    # Apply growth multiplier — scales crown linearly, keeps proportions
    semi_axis_x *= growth_multiplier
    semi_axis_y *= growth_multiplier

    # Clamp to canvas
    semi_axis_x = min(semi_axis_x, canvas_w * 0.42)
    semi_axis_y = min(semi_axis_y, canvas_h * 0.40)

    # Center: just above trunk top
    center_x = canvas_w / 2
    center_y = trunk_top[1] - semi_axis_y * 0.4

    # Eccentricity shift for dominant subtree
    eccentricity_x = 0.0
    if max_subtree_ratio > 0.5:
        eccentricity_x = semi_axis_x * (max_subtree_ratio - 0.5) * 0.6
        center_x += eccentricity_x

    points = _sample_superellipse(center_x, center_y, semi_axis_x, semi_axis_y, n)

    return CrownOutline(
        center_x=center_x,
        center_y=center_y,
        semi_axis_x=semi_axis_x,
        semi_axis_y=semi_axis_y,
        eccentricity_x=eccentricity_x,
        superellipse_n=n,
        points=points,
    )


# ---------------------------------------------------------------------------
# Step 3: Sector-based attractor distribution
# ---------------------------------------------------------------------------

def _distribute_attractors(
    crown: CrownOutline,
    root_stats: List[Dict],
    total_nodes: int,
    seed: int,
    growth_multiplier: float = 1.0,
) -> List[Sector]:
    rng = random.Random(seed)

    if not root_stats:
        return []

    # Weighted by subtree_size only — uniform, no spatial mastery bias
    weights = []
    for rs in root_stats:
        w = float(rs["subtree_size"])
        weights.append(w)
    total_weight = sum(weights)

    # Assign angular sectors from -pi/2 (top) going clockwise
    sectors: List[Sector] = []
    current_angle = -math.pi
    for i, rs in enumerate(root_stats):
        fraction = weights[i] / total_weight
        span = fraction * 2 * math.pi
        angle_start = current_angle
        angle_end = current_angle + span
        angle_center = (angle_start + angle_end) / 2

        # Sector attractor count proportional to weight, scaled by growth
        total_attractors = int((50 + 3 * total_nodes) * growth_multiplier)
        total_attractors = min(500, total_attractors)
        sector_count = max(3, int(total_attractors * weights[i] / total_weight))

        # Generate attractor points via reject sampling inside superellipse
        attractors: List[Tuple[float, float]] = []
        attempts = 0
        while len(attractors) < sector_count and attempts < sector_count * 30:
            # Uniform random in bounding box
            x = rng.uniform(
                crown.center_x - crown.semi_axis_x,
                crown.center_x + crown.semi_axis_x,
            )
            y = rng.uniform(
                crown.center_y - crown.semi_axis_y,
                crown.center_y + crown.semi_axis_y,
            )

            if _point_in_superellipse(
                x, y,
                crown.center_x, crown.center_y,
                crown.semi_axis_x, crown.semi_axis_y,
                crown.superellipse_n,
            ):
                # Check angular sector
                dx = x - crown.center_x
                dy = y - crown.center_y
                angle = math.atan2(dy, dx)
                if _angle_in_range(angle, angle_start, angle_end):
                    # Edge density falloff: lower acceptance near superellipse boundary
                    dx_n = abs((x - crown.center_x) / crown.semi_axis_x) if crown.semi_axis_x != 0 else 0
                    dy_n = abs((y - crown.center_y) / crown.semi_axis_y) if crown.semi_axis_y != 0 else 0
                    t = dx_n ** crown.superellipse_n + dy_n ** crown.superellipse_n
                    if rng.random() > (1.0 - t * t):
                        attempts += 1
                        continue
                    attractors.append((x, y))
            attempts += 1

        sectors.append(Sector(
            root_id=rs["id"],
            root_name=rs["name"],
            subtree_size=rs["subtree_size"],
            mastery_score=rs.get("mastery_score", 0.0),
            angle_start=angle_start,
            angle_end=angle_end,
            angle_center=angle_center,
            attractor_points=attractors,
        ))

        current_angle = angle_end

    return sectors


def _angle_in_range(angle: float, start: float, end: float) -> bool:
    """Check if angle is within [start, end], handling wraparound."""
    # Normalize all to [-pi, pi]
    a = math.atan2(math.sin(angle), math.cos(angle))
    if start <= end:
        return start <= a <= end
    # Wraps around
    return a >= start or a <= end
