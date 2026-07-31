"""
OCR engine adapters for the pdf_ocr pipeline.
Renders PDF pages to images, then runs OCR to extract text.

Supports multiple OCR backends (auto-detected):
- pix2text (recommended, recognizes text + LaTeX formulas + tables)
- easyocr (pure Python, good Chinese support)
- tesseract (faster, requires system install of tesseract-ocr)
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# ── Suppress noisy ONNX/CUDA warnings ──────────────────────────────────
# pix2text/RapidOCR log WARNINGs about CUDAExecutionProvider being
# unavailable on systems without onnxruntime-gpu. The fallback to CPU
# works fine — these messages only confuse users.

def _suppress_ocr_warnings():
    try:
        import logging as _logging
        _logging.getLogger("rapidocr").setLevel(_logging.ERROR)
        _logging.getLogger("rapidocr_onnxruntime").setLevel(_logging.ERROR)
        _logging.getLogger("cnocr").setLevel(_logging.ERROR)
        _logging.getLogger("cnstd").setLevel(_logging.ERROR)
    except Exception as e:
        logger.debug("Failed to suppress OCR logger levels: %s", e)
    try:
        import warnings as _warnings
        _warnings.filterwarnings("ignore", message=".*CUDAExecutionProvider.*")
    except Exception as e:
        logger.debug("Failed to suppress CUDA warnings: %s", e)

_suppress_ocr_warnings()

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

_easyocr_reader: object | None = None


def _get_easyocr_reader():
    """Lazy-load easyocr Reader. Singleton to avoid reloading models."""
    global _easyocr_reader
    if _easyocr_reader is None:
        logger.info("Loading easyocr models (first run downloads ~100MB)...")
        import easyocr
        _easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
    return _easyocr_reader


def _ocr_easyocr(page_images: list[bytes]) -> str:
    """Run easyocr on a list of page images (PNG bytes)."""
    reader = _get_easyocr_reader()

    from PIL import Image

    all_text: list[str] = []
    total = len(page_images)
    for i, img_bytes in enumerate(page_images):
        img = Image.open(io.BytesIO(img_bytes))
        results = reader.readtext(img, detail=0)
        page_text = '\n'.join(results)
        if page_text.strip():
            all_text.append(page_text.strip())
        if (i + 1) % 5 == 0 or i == total - 1:
            logger.info(f"easyocr page {i + 1}/{total}: {len(page_text)} chars")

    return '\n\n'.join(all_text)


def _ocr_tesseract(page_images: list[bytes], lang: str = 'chi_sim+eng') -> str:
    """Run tesseract OCR on a list of page images."""
    import pytesseract
    from PIL import Image

    all_text: list[str] = []
    total = len(page_images)
    for i, img_bytes in enumerate(page_images):
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, lang=lang)
        if text.strip():
            all_text.append(text.strip())
        if (i + 1) % 5 == 0 or i == total - 1:
            logger.info(f"tesseract page {i + 1}/{total}: {len(text)} chars")

    return '\n\n'.join(all_text)


# ── Pix2Text backend (formula-aware OCR) ─────────────────────────────

_pix2text_instance: object | None = None


def _get_pix2text():
    """Lazy-load Pix2Text singleton. Downloads models on first run (~200MB)."""
    global _pix2text_instance
    if _pix2text_instance is None:
        logger.info("Loading Pix2Text models (first run downloads ~200MB)...")
        from pix2text import Pix2Text
        _pix2text_instance = Pix2Text(device="cpu")
    return _pix2text_instance


def _ocr_pix2text(page_images: list[bytes]) -> str:
    """Run Pix2Text on a list of page images.

    P2T recognizes text, LaTeX formulas, and tables, outputting Markdown.
    Formulas are wrapped in $...$ (inline) and $$...$$ (block) delimiters
    that the frontend KaTeX renderer can display.
    """
    p2t = _get_pix2text()

    from PIL import Image

    all_text: list[str] = []
    total = len(page_images)
    for i, img_bytes in enumerate(page_images):
        img = Image.open(io.BytesIO(img_bytes))
        try:
            result = p2t.recognize_text_formula(img, return_text=True)
            page_text = result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.warning("pix2text recognize_text_formula failed, falling back to recognize: %s", e)
            # Fallback: try the full recognize API
            result = p2t.recognize(img)
            page_text = result.to_markdown() if hasattr(result, 'to_markdown') else str(result)
        if page_text.strip():
            all_text.append(page_text.strip())
        if (i + 1) % 5 == 0 or i == total - 1:
            logger.info(f"pix2text page {i + 1}/{total}: {len(page_text)} chars")

    return '\n\n'.join(all_text)


def _detect_available_backend() -> str | None:
    """Return the name of the first available OCR backend, or None.

    Priority: pix2text > easyocr > tesseract
    pix2text is preferred because it recognizes LaTeX formulas in addition to text.
    """
    try:
        import pix2text
        return "pix2text"
    except ImportError:
        pass
    try:
        import easyocr
        return "easyocr"
    except ImportError:
        pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return "tesseract"
    except Exception as e:
        logger.debug("Tesseract not available: %s", e)
        pass
    return None
