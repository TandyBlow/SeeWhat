"""
Space Colonization tree skeleton generator.
Replaces lsystem.py with a top-down approach:
  1. Crown outline (superellipse) from user data
  2. Sector-based attractor distribution
  3. Deterministic trunk + primary branches
  4. Space Colonization for fine branches
  5. da Vinci pipe model for thickness
  6. Root generation
"""
from skeleton_models import BranchNode, CrownOutline, Sector
from skeleton_stats import _compute_tree_stats, _count_descendants, _max_depth
from skeleton_crown import _generate_crown_outline, _distribute_attractors
from skeleton_geometry import _point_in_superellipse, _project_onto_superellipse
from skeleton_sc import _space_colonization
from skeleton_branches import _nodes_to_bezier_branches
from skeleton_thickness import _compute_thicknesses
from skeleton_core import generate_tree_skeleton
