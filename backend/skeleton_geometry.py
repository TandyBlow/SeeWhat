"""Pure mathematical helpers for superellipse geometry."""
import math
from typing import List, Tuple


def _point_in_superellipse(
    x: float, y: float,
    cx: float, cy: float,
    a: float, b: float, n: float,
) -> bool:
    dx = (x - cx) / a if a != 0 else 0
    dy = (y - cy) / b if b != 0 else 0
    return (abs(dx) ** n + abs(dy) ** n) <= 1.0


def _project_onto_superellipse(
    x: float, y: float,
    cx: float, cy: float,
    a: float, b: float, n: float,
) -> Tuple[float, float]:
    """Project a point onto the superellipse boundary along radial direction."""
    dx = x - cx
    dy = y - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return (cx, cy - b * 0.1)

    # Binary search for t where (t*dx/a)^n + (t*dy/b)^n = 1
    t_lo, t_hi = 0.0, 1.0
    for _ in range(30):
        t_mid = (t_lo + t_hi) / 2
        nx = t_mid * dx / a if a else 0
        ny = t_mid * dy / b if b else 0
        val = abs(nx) ** n + abs(ny) ** n
        if val < 1.0:
            t_lo = t_mid
        else:
            t_hi = t_mid
    t = (t_lo + t_hi) / 2
    return (cx + t * dx, cy + t * dy)


def _sample_superellipse(
    cx: float, cy: float,
    a: float, b: float, n: float,
    num_points: int = 64,
) -> List[Tuple[float, float]]:
    points = []
    for i in range(num_points):
        theta = 2 * math.pi * i / num_points
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        # Parametric superellipse
        x = a * _sgn(cos_t) * (abs(cos_t) ** (2 / n))
        y = b * _sgn(sin_t) * (abs(sin_t) ** (2 / n))
        points.append((cx + x, cy + y))
    return points


def _sgn(x: float) -> float:
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0
