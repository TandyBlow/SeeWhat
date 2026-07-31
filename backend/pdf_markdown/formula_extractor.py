"""
Formula extraction from PDF page images using pix2text + TexTeller.

Uses Unicode symbol density to detect candidate formula regions, crops just
those small patches from rendered page images, and feeds only the crops to
pix2text. TexTeller serves as fallback for low-confidence outputs.

This is MUCH faster than running pix2text on full pages (milliseconds per
crop vs tens of seconds per page).
"""

from __future__ import annotations

from .formula_core import extract_formulas
from .formula_detect import UNICODE_TO_LATEX, math_symbol_density, unicode_to_latex

__all__ = [
    "extract_formulas",
    "unicode_to_latex",
    "UNICODE_TO_LATEX",
    "math_symbol_density",
]
