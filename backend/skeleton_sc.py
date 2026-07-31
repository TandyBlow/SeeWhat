"""Space Colonization growth algorithm for fine branches (Step 5)."""
import math
import random
from typing import List, Dict, Tuple, Optional
from skeleton_models import BranchNode, CrownOutline, Sector
from skeleton_geometry import _point_in_superellipse, _project_onto_superellipse


# ---------------------------------------------------------------------------
# Step 5: Space Colonization
# ---------------------------------------------------------------------------

def _space_colonization(
    initial_nodes: List[BranchNode],
    sectors: List[Sector],
    crown: CrownOutline,
    seed: int,
    growth_step: float = 5.0,
    kill_distance: float = 8.0,
    influence_radius: float = 50.0,
    max_iterations: int = 300,
    max_branches: int = 600,
) -> List[BranchNode]:
    rng = random.Random(seed)

    # Collect all attractors with sector mapping
    all_attractors: List[Tuple[float, float]] = []
    attractor_sector_idx: List[int] = []
    for si, sector in enumerate(sectors):
        for pt in sector.attractor_points:
            all_attractors.append(pt)
            attractor_sector_idx.append(si)

    alive_nodes = list(initial_nodes)
    alive_attractors = list(range(len(all_attractors)))  # indices into all_attractors

    for iteration in range(max_iterations):
        if len(alive_nodes) >= max_branches:
            break
        if not alive_attractors:
            break

        # For each attractor, find nearest node within influence radius
        node_attractors: Dict[int, List[int]] = {}  # node_index -> [attractor_indices in alive_attractors]

        for ai_idx, ai in enumerate(alive_attractors):
            ax, ay = all_attractors[ai]
            best_node = -1
            best_dist = influence_radius

            for ni, node in enumerate(alive_nodes):
                d = math.hypot(node.position[0] - ax, node.position[1] - ay)
                if d < best_dist:
                    best_dist = d
                    best_node = ni

            if best_node >= 0:
                node_attractors.setdefault(best_node, []).append(ai_idx)

        if not node_attractors:
            break

        # Grow each node toward its attractors
        nodes_to_add: List[BranchNode] = []
        attractors_to_kill: set = set()

        for ni, ai_indices in node_attractors.items():
            node = alive_nodes[ni]

            # Average direction toward attractors
            avg_dx, avg_dy = 0.0, 0.0
            for ai_idx in ai_indices:
                ai = alive_attractors[ai_idx]
                ax, ay = all_attractors[ai]
                dx = ax - node.position[0]
                dy = ay - node.position[1]
                d = math.hypot(dx, dy)
                if d > 0:
                    avg_dx += dx / d
                    avg_dy += dy / d
            d_avg = math.hypot(avg_dx, avg_dy)
            if d_avg > 0:
                avg_dx /= d_avg
                avg_dy /= d_avg

            # Sector bias (15% weight)
            sector = _find_sector_for_root(sectors, node.root_id)
            if sector:
                # Direction toward sector center from crown center
                bias_dx = math.cos(sector.angle_center)
                bias_dy = math.sin(sector.angle_center)
                growth_dx = avg_dx * 0.85 + bias_dx * 0.15
                growth_dy = avg_dy * 0.85 + bias_dy * 0.15
            else:
                growth_dx = avg_dx
                growth_dy = avg_dy

            # Normalize
            d_g = math.hypot(growth_dx, growth_dy)
            if d_g > 0:
                growth_dx /= d_g
                growth_dy /= d_g

            # Small random perturbation
            rng.seed(seed + iteration * 1000 + ni)
            perturb_angle = rng.uniform(-0.05, 0.05)
            cos_p = math.cos(perturb_angle)
            sin_p = math.sin(perturb_angle)
            growth_dx, growth_dy = (
                growth_dx * cos_p - growth_dy * sin_p,
                growth_dx * sin_p + growth_dy * cos_p,
            )

            # New position
            new_x = node.position[0] + growth_dx * growth_step
            new_y = node.position[1] + growth_dy * growth_step

            # Hard boundary: project onto superellipse if outside
            if not _point_in_superellipse(
                new_x, new_y,
                crown.center_x, crown.center_y,
                crown.semi_axis_x, crown.semi_axis_y,
                crown.superellipse_n,
            ):
                new_x, new_y = _project_onto_superellipse(
                    new_x, new_y,
                    crown.center_x, crown.center_y,
                    crown.semi_axis_x, crown.semi_axis_y,
                    crown.superellipse_n,
                )
                # If projection is too close to current position, skip
                if math.hypot(new_x - node.position[0], new_y - node.position[1]) < 1:
                    continue

            new_node = BranchNode(
                position=(new_x, new_y),
                parent_index=ni,
                root_id=node.root_id,
                depth=node.depth + 1,
                thickness=0,
            )
            nodes_to_add.append(new_node)

            # Check kill distance
            for ai_idx in ai_indices:
                ai = alive_attractors[ai_idx]
                ax, ay = all_attractors[ai]
                if math.hypot(new_x - ax, new_y - ay) < kill_distance:
                    attractors_to_kill.add(ai_idx)

        # Apply growth
        for new_node in nodes_to_add:
            if len(alive_nodes) >= max_branches:
                break
            parent_idx = new_node.parent_index
            alive_nodes[parent_idx].children_indices.append(len(alive_nodes))
            alive_nodes.append(new_node)

        # Remove consumed attractors
        alive_attractors = [
            ai for idx, ai in enumerate(alive_attractors)
            if idx not in attractors_to_kill
        ]

    return alive_nodes


def _find_sector_for_root(sectors: List[Sector], root_id: str) -> Optional[Sector]:
    for s in sectors:
        if s.root_id == root_id:
            return s
    return sectors[0] if sectors else None
