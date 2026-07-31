"""da Vinci pipe model (Step 6): bottom-up leaf count then top-down thickness assignment."""
from typing import List
from skeleton_models import BranchNode


# ---------------------------------------------------------------------------
# Step 6: da Vinci pipe model
# ---------------------------------------------------------------------------

def _compute_thicknesses(
    all_nodes: List[BranchNode],
    trunk_base_thickness: float,
    trunk_top_thickness: float,
    min_thickness: float = 1.0,
    ref_thickness: float = 8.0,
) -> None:
    """Apply da Vinci pipe model: parent cross-section = sum of children."""
    if not all_nodes:
        return

    # Bottom-up: count leaves in each subtree
    leaf_counts: List[int] = [0] * len(all_nodes)

    def _count_leaves(idx: int) -> int:
        node = all_nodes[idx]
        if not node.children_indices:
            leaf_counts[idx] = 1
            return 1
        total = sum(_count_leaves(c) for c in node.children_indices)
        leaf_counts[idx] = total
        return total

    # Start from roots (nodes with no parent)
    root_indices = [i for i, n in enumerate(all_nodes) if n.parent_index is None]
    for ri in root_indices:
        _count_leaves(ri)

    max_leaves = max(leaf_counts) if leaf_counts else 1

    # Top-down: assign thickness based on leaf count
    for i, node in enumerate(all_nodes):
        if not node.children_indices:
            # Terminal node
            node.thickness = min_thickness
        else:
            # Power-law scaling: thickness = ref * (leaf_count / max_leaves)^0.6
            ratio = leaf_counts[i] / max_leaves if max_leaves > 0 else 0
            node.thickness = max(min_thickness, ref_thickness * (ratio ** 0.6))
