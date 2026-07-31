"""
Plain-text reading and shared pure-text utilities.
"""
import re


def parse_txt(file_path: str) -> str:
    """Parse plain text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_markdown(file_path: str) -> str:
    """Parse Markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def sanitize_control_chars(text: str) -> str:
    """Remove or replace ASCII control characters in text.

    Common PDF ligature mappings (font-specific, but widely observed):
    - U+001C (FS) → "fi" ligature
    - U+001B (ESC) → "ff" ligature
    - U+001D (GS) → "fl" ligature
    - U+001E (RS) → "ffi" ligature
    - U+001F (US) → "ffl" ligature

    Remaining control characters are replaced with a space so word
    boundaries are preserved and the frontend markdown parser doesn't
    choke on invalid XML/HTML characters.
    """
    # Map known PDF ligature control characters back to letters.
    # These mappings are heuristic — different PDFs may use different
    # encodings — but they are correct for the vast majority of cases.
    text = text.replace('\x1c', 'fi')   # FS → fi
    text = text.replace('\x1b', 'ff')   # ESC → ff
    text = text.replace('\x1d', 'fl')   # GS → fl
    text = text.replace('\x1e', 'ffi')  # RS → ffi
    text = text.replace('\x1f', 'ffl')  # US → ffl

    # Replace all remaining C0 control characters (except \t, \n, \r)
    # with a single space.  This keeps word boundaries intact so
    # "Retrieve" + U+0015 + "M" stays "Retrieve M" instead of becoming
    # "RetrieveM".
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1a]', ' ', text)

    # Replace C1 control characters (U+0080-U+009F) with a space.
    # These are invalid in HTML/XML and will break frontend parsing
    # when they survive into markdown content.
    text = re.sub(r'[\x80-\x9f]', ' ', text)

    return text


def is_text_garbled(text: str, min_sample: int = 40) -> bool:
    """Detect whether extracted PDF text is likely garbled (mojibake).

    Returns True when the text appears to be garbage rather than real content.
    Common causes: non-standard CMap/font encoding in Chinese PDFs that pymupdf
    cannot decode correctly.

    IMPORTANT: Call this on RAW pymupdf text, before _clean_pdf_text sanitizes
    control characters. Once sanitized, the signals this function looks for
    (control chars, PUA chars) are already removed.

    Heuristics applied:
    - Count characters by Unicode block (CJK, ASCII, PUA, controls)
    - If >5% of chars are in Private Use Area → garbled
    - If C0 control chars (excluding \\t\\n\\r) >0.3% → garbled
    - If C1 control chars (U+0080-U+009F) >0.1% → garbled
    - If text has CJK chars but at very low ratio (<3%) among non-ASCII → garbled
    - Empty or very short text is NOT considered garbled (handled by needs_ocr)
    """
    if not text or not text.strip():
        return False

    stripped = text.strip()
    if len(stripped) < min_sample:
        return False

    total = 0
    cjk = 0       # CJK Unified Ideographs + Extensions
    ascii_printable = 0
    pua = 0       # Private Use Area
    c0_control = 0  # C0 control chars (U+0000-U+001F, excluding tab/newline/CR)
    c1_control = 0  # C1 control chars (U+0080-U+009F)
    other_non_ascii = 0

    for ch in stripped:
        cp = ord(ch)
        total += 1
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF:
            cjk += 1
        elif 0x0020 <= cp <= 0x007E:
            ascii_printable += 1
        elif 0xE000 <= cp <= 0xF8FF:
            pua += 1
        elif cp < 0x0020 and cp not in (9, 10, 13):
            c0_control += 1
        elif 0x0080 <= cp <= 0x009F:
            c1_control += 1
        else:
            other_non_ascii += 1

    non_ascii = total - ascii_printable

    # C0 control characters (ligatures, encoding artifacts). Any real PDF
    # with >0.3% control chars has font encoding issues that will corrupt
    # math notation and break frontend markdown parsing.
    if c0_control > 0 and (c0_control / max(total, 1)) > 0.003:
        return True

    # C1 control characters are never legitimate in extracted PDF text,
    # but a small number (up to 1%) is tolerable — they're usually isolated
    # math symbols whose loss doesn't justify a multi-hour OCR run.
    if c1_control > 0 and (c1_control / max(total, 1)) > 0.01:
        return True

    # If >5% of characters are in Private Use Area, the text is garbled.
    # Legitimate PDFs rarely use PUA characters; >5% signals broken encoding.
    if pua > 0 and (pua / max(total, 1)) > 0.05:
        return True

    # If the text contains CJK characters but they represent <3% of non-ASCII
    # characters, the non-ASCII chars are likely encoding artifacts rather than
    # real content.
    if cjk > 0 and non_ascii > 0 and (cjk / non_ascii) < 0.03:
        return True

    # If non-ASCII dominates (>50%) but contains zero CJK and few ASCII chars,
    # the bytes were likely decoded as random Latin-1/Extended characters.
    if non_ascii > (total * 0.50) and cjk == 0 and ascii_printable < (total * 0.40):
        return True

    return False
