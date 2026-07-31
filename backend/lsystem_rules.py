"""
Pure L-system string operations: rule generation from child count and
string replacement iteration. No I/O, no randomness, no dependencies
beyond builtins.
"""


def generate_lsystem_rule(child_count: int) -> str:
    """
    Generate L-system rule based on child count.

    - child_count = 0 (leaf): F -> F
    - child_count = 1: F -> F[+F]
    - child_count = 2: F -> F[+F][-F]
    - child_count = 3: F -> F[+F][F][-F]
    - child_count = n: F -> F + n branches evenly distributed
    """
    if child_count == 0:
        return "F"
    elif child_count == 1:
        return "F[+F]"
    elif child_count == 2:
        return "F[+F][-F]"
    elif child_count == 3:
        return "F[+F][F][-F]"
    else:
        # Generate n branches evenly distributed
        branches = []
        for i in range(child_count):
            # Distribute angles evenly across ±25° range
            angle_offset = (i - (child_count - 1) / 2) * (50 / max(child_count - 1, 1))
            if angle_offset > 0:
                branches.append(f"[+F]")
            elif angle_offset < 0:
                branches.append(f"[-F]")
            else:
                branches.append(f"[F]")
        return "F" + "".join(branches)


def lsystem_iterate(axiom: str, rule: str, iterations: int) -> str:
    """
    Iterate L-system string replacement.
    """
    current = axiom
    for _ in range(iterations):
        current = current.replace("F", rule)
    return current
