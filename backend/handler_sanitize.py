"""
Response sanitization utilities for the refactored chat architecture.
Hard-enforces line-by-line output rules: anti-spoiler strip, 3-sentence cap,
and blockquote formatting.
"""
import re


# ── Response Sanitization ────────────────────────────────────────────────

# Chinese forward-reference patterns that indicate the AI is spoiling future content
# Strategy: any sentence containing temporal-forward markers is suspicious.
# Match aggressively — false positives (removing a non-spoiler sentence) are
# less harmful than false negatives (letting a spoiler through).
_FORWARD_REF_RE = re.compile(
    r'随后|后面[会要]|接下[来去]|下一[段句节章步个]|'
    r'之后[会要]?|在后面|稍后|将会|下文|往后|'
    r'我们接下来|我们后面|我们之后|我们稍后|'
    r'(?:后面|之后|接下来|稍后).*(?:会|要|将|来).*(?:介绍|讲|讨论|看到|学到|学习|说|提到)'
)

# Markdown link/image patterns — keep these as-is, they're fine
_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\([^\)]+\)')

_BLOCKQUOTE_LINE_RE = re.compile(r'^>\s')

_SENTENCE_END_RE = re.compile(r'[。！？；\.!\?]')


def _sanitize_line_by_line_response(ai_message: str, current_segment: str = "") -> str:
    """Post-process AI response to hard-enforce line-by-line rules.

    Three hard constraints applied at code level:
    1. Strip sentences that contain forward references (anti-spoiler)
    2. Enforce max 3 explanation sentences
    3. Ensure markdown blockquote ("> original") format
    """
    if not ai_message or not ai_message.strip():
        return ai_message

    msg = ai_message.strip()

    # ── 1. Enforce blockquote: if AI didn't quote the original, prepend it ──
    if not _BLOCKQUOTE_LINE_RE.match(msg):
        if current_segment:
            msg = f"> {current_segment}\n\n{msg}"

    # ── 2. Split blockquote from explanation ──
    # Find where the blockquote ends: first non-empty, non-"> " line
    lines = msg.split('\n')
    bq_end = 0
    for i, line in enumerate(lines):
        if _BLOCKQUOTE_LINE_RE.match(line) or line.strip() == '':
            bq_end = i + 1
        else:
            break

    if bq_end >= len(lines):
        return msg  # only blockquote, nothing to sanitize

    blockquote_part = '\n'.join(lines[:bq_end])
    explanation_text = '\n'.join(lines[bq_end:]).strip()

    if not explanation_text:
        return msg

    # ── 3. Strip forward-reference sentences ──
    raw_sentences = _SENTENCE_END_RE.split(explanation_text)
    # Re-join sentences with their terminators
    sentences: list[str] = []
    pos = 0
    for m in _SENTENCE_END_RE.finditer(explanation_text):
        sentences.append(explanation_text[pos:m.end()])
        pos = m.end()
    if pos < len(explanation_text):
        sentences.append(explanation_text[pos:])

    filtered: list[str] = []
    for sent in sentences:
        stripped = sent.strip()
        if not stripped:
            continue
        # Skip MD links/images — they look like forward refs but aren't
        cleaned = _MD_LINK_RE.sub('', stripped)
        if _FORWARD_REF_RE.search(cleaned):
            continue
        filtered.append(sent)

    if not filtered:
        # All explanation sentences were spoilers — keep just the blockquote
        return blockquote_part

    # ── 4. Hard cap at 3 sentences ──
    if len(filtered) > 3:
        filtered = filtered[:3]

    explanation_part = ''.join(filtered).strip()
    return f"{blockquote_part}\n\n{explanation_part}"
