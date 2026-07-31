"""
PDF rendering primitives for the OCR pipeline.
Renders PDF pages to images, then runs OCR to extract text.

Supports multiple OCR backends (auto-detected):
- pix2text (recommended, recognizes text + LaTeX formulas + tables)
- easyocr (pure Python, good Chinese support)
- tesseract (faster, requires system install of tesseract-ocr)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# OCR DPI when rendering pages. Higher = better accuracy but slower.
# 300 is the recommended minimum for Chinese characters (CJK glyphs need
# more detail than Latin letters). 200 produced unacceptably poor results.
OCR_RENDER_DPI = 300


def _render_pages(file_path: str, dpi: int = OCR_RENDER_DPI) -> list[bytes]:
    """Render all pages of a PDF to PNG images (in-memory bytes)."""
    import fitz

    doc = fitz.open(file_path)
    page_count = len(doc)
    images: list[bytes] = []
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes(output="png"))
            if (i + 1) % 5 == 0 or i == page_count - 1:
                logger.info(f"Rendered {i + 1}/{page_count} pages for OCR")
    finally:
        doc.close()
    return images


def get_page_count(file_path: str) -> int:
    """Return the number of pages in a PDF without rendering all of them."""
    import fitz

    doc = fitz.open(file_path)
    try:
        return len(doc)
    finally:
        doc.close()


def _render_page(file_path: str, page_num: int, dpi: int = OCR_RENDER_DPI) -> bytes:
    """Render a single page of a PDF to PNG bytes (in-memory)."""
    import fitz

    doc = fitz.open(file_path)
    try:
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes(output="png")
    finally:
        doc.close()


def extract_formulas_with_bbox(file_path: str) -> list:
    """Extract formula regions from PDF using pix2text + TexTeller cross-validation.

    Thin wrapper around pdf_markdown.formula_extractor.extract_formulas.
    Returns list of LabeledSpan objects with MATH/DISPLAY_MATH labels and
    character positions aligned to PyMuPDF text spans.

    Requires spans from extract_spans_from_pdf() for spatial alignment.
    """
    from pdf_markdown.formula_extractor import extract_formulas
    from pdf_markdown.span_extractor import extract_spans

    spans = extract_spans(file_path)
    if not spans:
        return []
    return extract_formulas(file_path, spans)
