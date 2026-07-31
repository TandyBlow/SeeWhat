"""Data classes shared by every step of the Space Colonization tree generator."""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class CrownOutline:
    center_x: float
    center_y: float
    semi_axis_x: float
    semi_axis_y: float
    eccentricity_x: float
    superellipse_n: float
    points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class Sector:
    root_id: str
    root_name: str
    subtree_size: int
    mastery_score: float
    angle_start: float
    angle_end: float
    angle_center: float
    attractor_points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class BranchNode:
    """Internal node in the Space Colonization graph."""
    position: Tuple[float, float]
    parent_index: Optional[int]
    children_indices: List[int] = field(default_factory=list)
    root_id: str = ""
    depth: int = 0
    thickness: float = 0.0


@dataclass
class ForkPoint:
    position: Tuple[float, float]
    radius: float
    is_primary: bool
    root_id: str
