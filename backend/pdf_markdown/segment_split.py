"""
Low-level sentence splitting.

The list-marker regex, the latin split threshold, and the raw tokenizer that
preserves \n (inter-line) and \n\n (paragraph) boundaries so char_start/
char_end stay aligned with the spans-based text.
"""

from __future__ import annotations

import re

# List-marker patterns that signal a new item should start its own segment
_LIST_MARKER_RE = re.compile(
    r'^'
    r'(?:'
    r'\([a-z]\)'        # (a), (b), (c)
    r'|\([\d]+\)'       # (1), (2), (3)
    r'|\[[a-z]\]'       # [a], [b], [c]
    r'|\[[\d]+\]'       # [1], [2], [3]
    r'|[ivxlcdm]+[\.\)]' # i., ii., iii., iv.)
    r'|[\d]+[\.\)]'     # 1., 2., 3., 1)
    r'|[a-z][\.\)]'     # a., b., c.
    r')\s'
)

_LATIN_SPLIT_MIN_LEN = 80  # only split on ". Capital" when buffer exceeds this


def _split_into_raw_sentences(text: str) -> list[tuple[str, int, int]]:
    """Split text into raw sentence-like units with their char positions.

    Returns list of (sentence_text, char_start, char_end).

    Paragraph boundaries are \n\n (from spans_to_text). Single \n is kept
    as-is — it represents inter-line breaks within a paragraph and must be
    preserved for offset alignment.
    """
    if not text.strip():
        return []

    raw_parts: list[tuple[str, int, int]] = []
    pos = 0
    buf: list[str] = []
    buf_start = 0

    i = 0
    while i < len(text):
        ch = text[i]

        # Paragraph break: \n\n or more — split here
        if ch == '\n':
            # Count consecutive newlines
            j = i
            while j < len(text) and text[j] == '\n':
                j += 1
            newline_count = j - i

            if newline_count >= 2:
                # Paragraph break — flush buffer
                if buf:
                    raw_parts.append(("".join(buf), buf_start, i))
                    buf = []
                i = j
                buf_start = i
                continue
            else:
                # Single \n — check if next line starts with a list marker
                # If so, treat as a split point (each list item = own segment)
                rest = text[i + 1:]
                if rest and _LIST_MARKER_RE.match(rest):
                    # Flush current buffer, treat \n as paragraph-level split
                    if buf:
                        raw_parts.append(("".join(buf), buf_start, i))
                        buf = []
                    i += 1  # skip the \n itself
                    buf_start = i
                    continue
                else:
                    # Regular mid-paragraph line break — keep \n
                    buf.append('\n')
                    i += 1
                    continue

        # Chinese sentence end
        if ch in '。！？':
            buf.append(ch)
            i += 1
            raw_parts.append(("".join(buf), buf_start, i))
            buf = []
            buf_start = i
            continue

        # Latin sentence end — only split if buffer is long enough
        if ch in '.!?' and i + 1 < len(text):
            after = text[i + 1]
            buf_len = len(''.join(buf))
            # Only split ". " + Capital when we have a substantial buffer
            if after == ' ' and i + 2 < len(text) and text[i + 2].isupper() and buf_len >= _LATIN_SPLIT_MIN_LEN:
                buf.append(ch)
                buf.append(' ')
                i += 2
                raw_parts.append(("".join(buf), buf_start, i))
                buf = []
                buf_start = i
                continue
            # End of paragraph after punctuation
            if after == '\n':
                buf.append(ch)
                i += 1
                raw_parts.append(("".join(buf), buf_start, i))
                buf = []
                # Skip trailing newlines (paragraph break)
                while i < len(text) and text[i] == '\n':
                    i += 1
                buf_start = i
                continue

        buf.append(ch)
        i += 1

    # Remaining
    if buf:
        raw_parts.append(("".join(buf), buf_start, len(text)))

    return raw_parts
