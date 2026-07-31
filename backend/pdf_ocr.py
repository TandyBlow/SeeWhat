"""
OCR pipeline for scanned / image-based PDFs.
Renders PDF pages to images, then runs OCR to extract text.

Supports multiple OCR backends (auto-detected):
- pix2text (recommended, recognizes text + LaTeX formulas + tables)
- easyocr (pure Python, good Chinese support)
- tesseract (faster, requires system install of tesseract-ocr)
"""

from __future__ import annotations

from ocr_backends import _detect_available_backend
from ocr_backends import _easyocr_reader
from ocr_backends import _get_easyocr_reader
from ocr_backends import _get_pix2text
from ocr_backends import _ocr_easyocr
from ocr_backends import _ocr_pix2text
from ocr_backends import _ocr_tesseract
from ocr_backends import _pix2text_instance
from ocr_backends import _suppress_ocr_warnings
from ocr_core import MIN_AVG_CHARS_PER_PAGE
from ocr_core import MIN_CHARS_FOR_TEXT_PDF
from ocr_core import needs_ocr
from ocr_core import ocr_page
from ocr_core import ocr_pdf
from ocr_render import OCR_RENDER_DPI
from ocr_render import _render_page
from ocr_render import _render_pages
from ocr_render import extract_formulas_with_bbox
from ocr_render import get_page_count

__all__ = [
    "_suppress_ocr_warnings",
    "_get_easyocr_reader",
    "_easyocr_reader",
    "_ocr_easyocr",
    "_ocr_tesseract",
    "_pix2text_instance",
    "_get_pix2text",
    "_ocr_pix2text",
    "MIN_CHARS_FOR_TEXT_PDF",
    "MIN_AVG_CHARS_PER_PAGE",
    "OCR_RENDER_DPI",
    "_render_pages",
    "get_page_count",
    "_render_page",
    "_detect_available_backend",
    "needs_ocr",
    "ocr_pdf",
    "extract_formulas_with_bbox",
    "ocr_page",
]
