"""
Two-layer validation for LLM structural annotations.

Layer 1: Deterministic rule checks (no LLM, always runs).
Layer 2: LLM review of rule-violating regions.

Re-exports the public API from the split rule-check modules.
"""

from __future__ import annotations

from .review_rules import (
    check_annotation_rules,
    filter_error_violations,
    filter_warning_violations,
)
from .review_llm import llm_review_violations

__all__ = [
    "check_annotation_rules",
    "llm_review_violations",
    "filter_error_violations",
    "filter_warning_violations",
]
