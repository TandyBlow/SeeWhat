"""
Orchestrator: the public extract_formulas entry point plus the span-bbox →
pixel-crop geometry helper. Groups regions by page, lazily caches rendered
pages, classifies inline vs display math, OCRs display candidates and
filters by confidence.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from .annotation_schema import StructuralLabel, LabeledSpan
from .span_extractor import Span

from .formula_detect import UNICODE_TO_LATEX, detect_math_regions, unicode_to_latex
from .formula_ocr import _crop_and_ocr, _render_page_image

logger = logging.getLogger(__name__)


def _get_span_bbox_in_pixels(
    spans: list[Span],
    page_height_px: float,
    dpi: int = 300,
    margin: int = 10,
) -> tuple[int, int, int, int] | None:
    """Convert span bounding boxes (PDF points) to pixel crop region with margin.

    Returns (x0, y0, x1, y1) in pixel coordinates, or None if spans have no bbox.
    """
    if not spans:
        return None

    scale = dpi / 72.0
    x0 = min(s.bbox[0] for s in spans if s.bbox[2] > s.bbox[0])
    y0 = min(s.bbox[1] for s in spans if s.bbox[3] > s.bbox[1])
    x1 = max(s.bbox[2] for s in spans)
    y1 = max(s.bbox[3] for s in spans)

    if x1 <= x0 or y1 <= y0:
        return None

    px0 = max(0, int(x0 * scale) - margin)
    py1 = int((page_height_px - y0 * scale)) + margin  # flip Y
    px1 = int(x1 * scale) + margin
    py0 = max(0, int((page_height_px - y1 * scale)) - margin)

    return (px0, py0, px1, py1)


def extract_formulas(
    file_path: str,
    spans: list[Span],
    confidence_threshold: float = 0.7,
    max_ocr_regions: int = 15,
) -> list[LabeledSpan]:
    """Extract formulas by detecting candidate regions and cropping.

    1. Detect math regions via Unicode symbol density
    2. Classify as inline (MATH) or display (DISPLAY_MATH) by width
    3. Only OCR display-math candidates — inline math uses span text directly
    4. Mark remaining regions as MATH with density-based confidence
    5. Filter by confidence_threshold

    OCR is the slowest stage (~5s per crop). Skipping inline math saves
    most of the time — a page with 56 regions typically has <5 display
    formulas but 50+ inline variables that don't need OCR.
    """
    # Step 1: Detect candidate regions
    math_regions = detect_math_regions(spans)

    if not math_regions:
        logger.info("No math regions detected")
        return []

    # Group regions by page
    by_page: dict[int, list] = defaultdict(list)
    for start, end, density, region_spans in math_regions:
        page = region_spans[0].page_number
        by_page[page].append((start, end, density, region_spans))

    # Cache rendered page images
    page_images: dict[int, tuple[bytes, float, float]] = {}

    labeled: list[LabeledSpan] = []

    for page_num, regions in sorted(by_page.items()):
        # Lazy render page
        if page_num not in page_images:
            try:
                page_images[page_num] = _render_page_image(file_path, page_num)
            except Exception as e:
                logger.warning(f"Failed to render page {page_num}: {e}")
                # Fall back to density-only labels
                for start, end, density, _ in regions:
                    labeled.append(LabeledSpan(
                        label=StructuralLabel.MATH,
                        char_start=start,
                        char_end=end,
                        confidence=density,
                    ))
                continue

        img_bytes, page_w, page_h = page_images[page_num]

        # Classify regions: only OCR display-math candidates
        ocr_count = 0
        for start, end, density, region_spans in regions:
            # Determine if this region is display math (wide) or inline (narrow)
            crop_bbox = _get_span_bbox_in_pixels(region_spans, page_h)
            if crop_bbox is None:
                labeled.append(LabeledSpan(
                    label=StructuralLabel.MATH,
                    char_start=start,
                    char_end=end,
                    confidence=density,
                ))
                continue

            crop_w = crop_bbox[2] - crop_bbox[0]
            is_display = crop_w > page_w * 0.4

            if is_display and ocr_count < max_ocr_regions:
                # OCR only display-math candidates
                latex = _crop_and_ocr(img_bytes, crop_bbox)
                ocr_count += 1

                if latex and latex.strip():
                    labeled.append(LabeledSpan(
                        label=StructuralLabel.DISPLAY_MATH,
                        char_start=start,
                        char_end=end,
                        confidence=0.7,
                        latex_text=latex.strip(),
                    ))
                else:
                    # OCR failed or produced garbage — don't label as math,
                    # let text flow as regular paragraph instead
                    logger.info(f"Skipping display-math label for region [{start}:{end}] (no valid OCR)")
            else:
                # Inline math — use Unicode-to-LaTeX mapping instead of OCR
                raw_text = "".join(s.text for s in region_spans)
                latex_text = unicode_to_latex(raw_text)
                # Check if mapping produced any LaTeX (vs just plain text)
                has_latex = any(ch in UNICODE_TO_LATEX for ch in raw_text)
                confidence = max(density, 0.8) if has_latex else density
                if has_latex:
                    labeled.append(LabeledSpan(
                        label=StructuralLabel.MATH,
                        char_start=start,
                        char_end=end,
                        confidence=confidence,
                        latex_text=latex_text,
                    ))
                else:
                    # No LaTeX mapping available — keep as regular text, don't label
                    pass

        logger.info(f"Page {page_num + 1}: OCR'd {ocr_count} display formulas, "
                    f"skipped {len(regions) - ocr_count} inline regions")

    # Filter by confidence threshold
    labeled = [f for f in labeled if f.confidence >= confidence_threshold]

    labeled.sort(key=lambda f: f.char_start)
    logger.info(f"Total math regions: {len(labeled)} (after confidence filter)")
    return labeled
