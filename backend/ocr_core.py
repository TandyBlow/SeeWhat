"""
OCR orchestration API for the pdf_ocr pipeline.
Renders PDF pages to images, then runs OCR to extract text.

Supports multiple OCR backends (auto-detected):
- pix2text (recommended, recognizes text + LaTeX formulas + tables)
- easyocr (pure Python, good Chinese support)
- tesseract (faster, requires system install of tesseract-ocr)
"""

from __future__ import annotations

import io
import logging
from typing import Callable

from ocr_backends import _detect_available_backend
from ocr_backends import _get_pix2text
from ocr_backends import _get_easyocr_reader
from ocr_backends import _ocr_pix2text
from ocr_backends import _ocr_easyocr
from ocr_backends import _ocr_tesseract
from ocr_render import OCR_RENDER_DPI
from ocr_render import _render_pages
from ocr_render import _render_page

logger = logging.getLogger(__name__)

# Thresholds for auto-OCR decision
MIN_CHARS_FOR_TEXT_PDF = 100       # fewer than this total -> likely scanned
MIN_AVG_CHARS_PER_PAGE = 50        # fewer than this per page -> likely scanned


def needs_ocr(file_path: str) -> str | None:
    """Check whether a PDF needs OCR, and why.

    Returns a reason string if OCR is recommended, or None if the PDF text
    is adequate.  Reasons:
    - "text_too_short": scanned/image-based PDF with very little extractable text
    - "text_garbled": text extraction produced garbled characters (PUA chars,
      C1 control chars, mojibake patterns) that sanitize_control_chars
      CANNOT fix — OCR is the only way to recover readable text

    Ligature control characters (U+001B-U+001F) are NOT considered garbled
    because sanitize_control_chars maps them back to the correct letters.
    Only unfixable degradation (PUA, C1 controls, non-ASCII mojibake)
    triggers the OCR recommendation.
    """
    import fitz

    doc = fitz.open(file_path)
    try:
        page_count = max(len(doc), 1)
        total_chars = 0
        raw_parts: list[str] = []
        for page in doc:
            text = page.get_text("text").strip()
            total_chars += len(text)
            raw_parts.append(text)

        # Check 1: too little text (scanned/image-based PDF)
        if total_chars < MIN_CHARS_FOR_TEXT_PDF:
            return "text_too_short"
        if (total_chars / page_count) < MIN_AVG_CHARS_PER_PAGE:
            return "text_too_short"

        # Check 2: garbled text (font encoding issues).
        # Apply sanitize_control_chars FIRST so that fixable ligature
        # issues (U+001B-U+001F) don't trigger a needless hour-long OCR.
        # Then check the "fixed" text — if it's still garbled (PUA, C1,
        # mojibake), OCR is genuinely needed.
        from file_parser import is_text_garbled, sanitize_control_chars
        raw_text = '\n'.join(raw_parts)
        fixed_text = sanitize_control_chars(raw_text)
        if is_text_garbled(fixed_text):
            return "text_garbled"

        return None
    finally:
        doc.close()


def ocr_pdf(file_path: str, backend: str | None = None, dpi: int = OCR_RENDER_DPI) -> str:
    """Extract text from a scanned/image-based PDF using OCR.

    Args:
        file_path: Path to the PDF file.
        backend: OCR backend name ('easyocr', 'tesseract') or None for auto-detect.
        dpi: Rendering DPI for page images (higher = better accuracy, slower).

    Returns:
        Extracted text content.

    Raises:
        RuntimeError: If no OCR backend is available.
        ImportError: If the specified backend is not installed.
    """
    # Resolve backend
    if backend is None:
        backend = _detect_available_backend()
    if backend is None:
        raise RuntimeError(
            "No OCR backend available. Install one:\n"
            "  pip install easyocr          (recommended, pure Python)\n"
            "  pip install pytesseract       (requires tesseract system install)"
        )

    # Render pages
    logger.info(f"Rendering PDF pages at {dpi} DPI for OCR...")
    page_images = _render_pages(file_path, dpi=dpi)
    if not page_images:
        return ""

    # Run OCR
    backends: dict[str, Callable[[list[bytes]], str]] = {
        "pix2text": _ocr_pix2text,
        "easyocr": _ocr_easyocr,
        "tesseract": _ocr_tesseract,
    }
    ocr_fn = backends.get(backend)
    if ocr_fn is None:
        raise ValueError(f"Unknown OCR backend: {backend}. Options: {list(backends)}")

    logger.info(f"Running OCR with {backend} on {len(page_images)} pages...")
    raw_text = ocr_fn(page_images)
    logger.info(f"OCR complete: {len(raw_text)} chars extracted")

    # Apply the same text cleaning used by the main parser
    from file_parser import _clean_pdf_text
    return _clean_pdf_text(raw_text)


def ocr_page(file_path: str, page_num: int, dpi: int = OCR_RENDER_DPI,
             backend: str | None = None) -> str:
    """OCR a single page of a PDF. Returns extracted text for that page.

    Designed for the background OCR task manager to process pages one at a
    time with progress reporting between pages.

    Args:
        file_path: Path to the PDF file.
        page_num: Zero-based page index.
        dpi: Rendering DPI.
        backend: OCR backend name or None for auto-detect.

    Returns:
        Extracted text content for the page (not cleaned — caller should
        accumulate and clean the full result).
    """
    if backend is None:
        backend = _detect_available_backend()
    if backend is None:
        raise RuntimeError("No OCR backend available")

    from PIL import Image

    img_bytes = _render_page(file_path, page_num, dpi)
    img = Image.open(io.BytesIO(img_bytes))

    if backend == "pix2text":
        p2t = _get_pix2text()
        try:
            result = p2t.recognize_text_formula(img, return_text=True)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.warning("pix2text recognize_text_formula failed in ocr_page, falling back: %s", e)
            result = p2t.recognize(img)
            return result.to_markdown() if hasattr(result, 'to_markdown') else str(result)

    elif backend == "easyocr":
        reader = _get_easyocr_reader()
        results = reader.readtext(img, detail=0)
        return '\n'.join(results)

    elif backend == "tesseract":
        import pytesseract
        return pytesseract.image_to_string(img, lang='chi_sim+eng')

    else:
        raise ValueError(f"Unknown OCR backend: {backend}")
