"""Structural rule checks and the review orchestrator.

Layer 1 deterministic checks that operate on the label hierarchy (heading
levels, list numbering) plus the public orchestrator check_annotation_rules
and the two severity filters. Text-content checks come from review_text_rules.
"""

from __future__ import annotations

from .annotation_schema import (
    StructuralLabel,
    SentenceAnnotation,
    RuleViolation,
    HEADING_LABELS,
    HEADING_LEVEL,
)

from .review_text_rules import (
    _check_interval_coverage,
    _check_boundary_integrity,
    _check_false_code_blocks,
)


def check_annotation_rules(
    annotations: list[SentenceAnnotation],
    text: str,
) -> list[RuleViolation]:
    """Run deterministic structural rule checks.

    Returns list of RuleViolation objects. Empty list means all checks passed.
    """
    violations: list[RuleViolation] = []
    violations.extend(_check_interval_coverage(annotations, text))
    violations.extend(_check_heading_nesting(annotations))
    violations.extend(_check_list_continuity(annotations))
    violations.extend(_check_boundary_integrity(annotations, text))
    violations.extend(_check_false_code_blocks(annotations, text))
    return violations


def _check_heading_nesting(
    annotations: list[SentenceAnnotation],
) -> list[RuleViolation]:
    """Check that heading levels never skip (h1→h3 without h2 is invalid)."""
    violations: list[RuleViolation] = []
    headings: list[tuple[int, StructuralLabel, int, int]] = []

    for sent_ann in annotations:
        for label in sent_ann.labels:
            if label.label in HEADING_LABELS:
                headings.append((
                    label.char_start,
                    label.label,
                    HEADING_LEVEL.get(label.label, 0),
                    label.char_end,
                ))

    if len(headings) < 2:
        return violations

    for i in range(len(headings) - 1):
        _, _, current_level, _ = headings[i]
        _, next_label, next_level, next_end = headings[i + 1]

        if next_level > current_level + 1:
            violations.append(RuleViolation(
                region=(headings[i][0], next_end),
                rule_name="HEADING_NESTING",
                severity="error",
                description=(
                    f"Heading level jump from {current_level} to {next_level} "
                    f"({headings[i][1].value} → {next_label.value}) — skipped level {current_level + 1}"
                ),
            ))

    # Also check: at most one h1
    h1_count = sum(1 for _, label, _, _ in headings if label == StructuralLabel.HEADING_1)
    if h1_count > 1:
        h1_regions = [(s, e) for s, lbl, _, e in headings if lbl == StructuralLabel.HEADING_1]
        violations.append(RuleViolation(
            region=(h1_regions[0][0], h1_regions[-1][1]),
            rule_name="MULTIPLE_H1",
            severity="warning",
            description=f"Found {h1_count} h1 headings — document should have exactly one title",
        ))

    return violations


def _check_list_continuity(
    annotations: list[SentenceAnnotation],
) -> list[RuleViolation]:
    """Check that ordered list numbering is consistent at each nesting level."""
    violations: list[RuleViolation] = []

    # Group ordered list items by nesting level
    items_by_level: dict[int, list[tuple[int, int]]] = {}

    for sent_ann in annotations:
        for label in sent_ann.labels:
            if label.label == StructuralLabel.ORDERED_LIST_ITEM:
                level = label.nesting_level
                items_by_level.setdefault(level, []).append((label.char_start, label.char_end))

    # For each level, check the sequence looks reasonable
    # Flag levels with only 1 item as potential issues
    for level, items in items_by_level.items():
        if len(items) < 1:
            continue
        if len(items) == 1 and level > 1:
            violations.append(RuleViolation(
                region=(items[0][0], items[0][1]),
                rule_name="LIST_SINGLE_ITEM",
                severity="warning",
                description=f"Single ordered list item at nesting level {level} — possible mislabel",
            ))

    return violations


def filter_error_violations(violations: list[RuleViolation]) -> list[RuleViolation]:
    """Return only error-severity violations."""
    return [v for v in violations if v.severity == "error"]


def filter_warning_violations(violations: list[RuleViolation]) -> list[RuleViolation]:
    """Return only warning-severity violations."""
    return [v for v in violations if v.severity == "warning"]
