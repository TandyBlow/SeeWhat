"""
Font-metadata-based PDF-to-Markdown reconstruction (two-pass font-size
analysis + heading/formatting synthesis).
"""
from collections import Counter

from parser_pdf_spans import _is_mono_font, _is_bullet_start, _format_spans


def parse_pdf_markdown(file_path: str) -> str:
    """Parse PDF and reconstruct Markdown formatting from font metadata.

    Uses PyMuPDF's ``get_text("dict")`` API to read font size, weight,
    italic flag, monospace flag, and bounding-box position for every span.
    These signals are mapped back to Markdown:

    - Font size (document-level relative scaling) → headings (h1–h4)
    - Flags bit 4 (bold) → ``**bold**``
    - Flags bit 1 (italic) → ``*italic*``
    - Flags bit 3 / font name → `` `code` `` or fenced code blocks
    - Bullet characters + indentation → unordered/ordered list items

    Returns clean Markdown text suitable for frontend rendering.
    """
    try:
        import fitz
    except ImportError:
        raise ImportError("pymupdf is required. Install: pip install pymupdf")

    doc = fitz.open(file_path)

    # ── Pass 1: collect all font sizes across the document ──────────
    all_sizes: list[float] = []
    for page in doc:
        page_dict = page.get_text("dict")
        for block in page_dict["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    all_sizes.append(round(span["size"], 1))

    if not all_sizes:
        doc.close()
        return ""

    # Document-level body-size detection (mode of all font sizes)
    size_counts = Counter(all_sizes)
    # Ignore very rare sizes (< 0.5% of spans) — they're usually artifacts
    min_count = max(len(all_sizes) * 0.005, 2)
    common_sizes = {s for s, c in size_counts.items() if c >= min_count}
    body_size = max(common_sizes, key=lambda s: size_counts[s]) if common_sizes else Counter(all_sizes).most_common(1)[0][0]

    # Heading sizes: sizes > body * 1.1, sorted descending → h1..h4
    heading_candidates = sorted(
        [s for s in common_sizes if s > body_size * 1.1],
        reverse=True
    )[:4]
    size_to_level: dict[float, int] = {}
    for i, size in enumerate(heading_candidates):
        size_to_level[size] = i + 1

    # ── Pass 2: generate Markdown ──────────────────────────────────
    all_pages_md: list[str] = []

    for page in doc:
        page_dict = page.get_text("dict")
        page_lines: list[str] = []
        prev_was_code_block = False

        for block in page_dict["blocks"]:
            if block.get("type") != 0:
                # Image block — signal a gap, but don't insert excessive blanks
                if page_lines and page_lines[-1] != "":
                    page_lines.append("")
                continue

            block_lines = block.get("lines", [])
            if not block_lines:
                continue

            # Check if this entire block is monospace → fenced code block
            block_all_mono = True
            for line in block_lines:
                for span in line["spans"]:
                    flags = span.get("flags", 0)
                    font = span.get("font", "")
                    if not (bool(flags & 8) or _is_mono_font(font)):
                        block_all_mono = False
                        break
                if not block_all_mono:
                    break

            if block_all_mono and len(block_lines) >= 1:
                code_parts: list[str] = []
                for line in block_lines:
                    text = "".join(sp["text"] for sp in line["spans"]).rstrip('\n')
                    code_parts.append(text)
                if prev_was_code_block:
                    # Merge into previous code block (separated by a page break
                    # but part of the same listing)
                    page_lines[-1] = page_lines[-1].rstrip('\n') + '\n' + '\n'.join(code_parts)
                else:
                    page_lines.append("```\n" + "\n".join(code_parts) + "\n```")
                page_lines.append("")
                prev_was_code_block = True
                continue

            prev_was_code_block = False

            # Separate blocks with a blank line
            if page_lines and page_lines[-1] != "":
                page_lines.append("")

            for line in block_lines:
                spans = line["spans"]
                if not spans:
                    continue

                max_size = max(round(sp["size"], 1) for sp in spans)
                line_text_raw = "".join(sp["text"] for sp in spans).strip()

                heading_level = size_to_level.get(max_size)

                # Fallback heuristic: short line (< 200 chars) with large font
                if heading_level is None and max_size > body_size * 1.2:
                    ratio = max_size / body_size
                    if ratio > 2.2:
                        heading_level = 1
                    elif ratio > 1.7:
                        heading_level = 2
                    elif ratio > 1.35:
                        heading_level = 3

                if heading_level and len(line_text_raw) < 200:
                    formatted = "".join(_format_spans(spans)).strip()
                    if formatted:
                        page_lines.append(f"{'#' * heading_level} {formatted}")
                else:
                    formatted = "".join(_format_spans(spans))
                    stripped = formatted.strip()
                    if not stripped:
                        page_lines.append("")
                    elif _is_bullet_start(stripped):
                        page_lines.append(stripped)
                    else:
                        page_lines.append(formatted)

        # Clean trailing blanks
        while page_lines and page_lines[-1] == "":
            page_lines.pop()
        while page_lines and page_lines[0] == "":
            page_lines.pop(0)

        if page_lines:
            all_pages_md.append("\n".join(page_lines))

    doc.close()
    return "\n\n".join(all_pages_md)
