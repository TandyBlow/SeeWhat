"""
Post-processing of assembled markdown.

Newline/whitespace normalization (_normalize_whitespace), union/intersection
operator spacing (_fix_math_operator_spacing), $...$ delimiter cleanup via
paired-delimiter walk (_clean_inline_math_spacing), hard-break and unicode-math
text cleanup (_hard_breaks, _clean_unicode_math), plus the dead-but-preserved
_fix_merged_spacing/_looks_like_two_words pair.
"""

from __future__ import annotations

import re


def _fix_merged_spacing(md: str) -> str:
    """Fix spacing artifacts from italic/bold marker suppression.

    When italic markers are removed, spaces that were at marker boundaries
    can be lost, creating concatenated words like "Itrepresents" or "isyear".
    This function re-inserts spaces where two English words were joined.
    """
    # Pattern: lowercase letter directly followed by an uppercase or
    # another word start within a longer word (camel-case-like artifact)
    # e.g. "Itrepresents" → "It represents", "isyear" → "is year"
    # But NOT "CST" or "AI" (legitimate abbreviations)
    md = re.sub(
        r'(?<=[a-z])(?=[A-Z][a-z])',
        ' ',
        md
    )
    # Pattern: common word boundary loss — short word glued to longer word
    # e.g. "basicproperties" → "basic properties"
    # Check by seeing if splitting creates two common English patterns
    md = re.sub(
        r'\b([a-z]{2,5})([a-z]{4,})\b',
        lambda m: f"{m.group(1)} {m.group(2)}" if _looks_like_two_words(m.group(1), m.group(2)) else m.group(0),
        md
    )
    return md


def _looks_like_two_words(prefix: str, suffix: str) -> bool:
    """Check if prefix+suffix looks like two English words glued together."""
    # Short common English words that often get glued
    common_prefixes = {
        'is', 'it', 'in', 'of', 'on', 'to', 'be', 'we', 'he', 'an', 'as',
        'or', 'so', 'no', 'do', 'if', 'by', 'up', 'am', 'me', 'my',
        'the', 'and', 'for', 'but', 'not', 'all', 'any', 'can', 'had',
        'was', 'are', 'has', 'its', 'our', 'who', 'how', 'out',
    }
    return prefix.lower() in common_prefixes


def _fix_math_operator_spacing(md: str) -> str:
    """Insert spaces where union/intersection operators are glued to braces.

    In PDF spans, ∪{ and ∩{ appear as one chunk without a space, but in
    readable math notation these should be ∪ { and ∩ { (e.g. {a} ∪ {b}).
    Only fixes the operator+brace pattern — other cases like ΩX or |Ω|
    are valid math notation without spaces.
    """
    md = md.replace('∪{', '∪ {')
    md = md.replace('∩{', '∩ {')
    return md


def _clean_inline_math_spacing(md: str) -> str:
    """Remove leading/trailing spaces inside $...$ delimiters and fix
    LaTeX command spacing.

    Fixes:
    - "$ \\emptyset $" -> "$\\emptyset$" (strip whitespace inside delimiters)
    - "$\\inS$" -> "$\\in S$" (space between LaTeX command and letter)
    - "$\\Omega$X" -> "$\\Omega$ X" (space after closing delimiter)

    Preserves spaces that are part of the expression (e.g. "$\\alpha, \\beta$")

    Processes by explicitly pairing opening/closing $ delimiters instead
    of using regex, to prevent cross-expression matching that would strip
    spaces between adjacent $...$ expressions.
    """
    # Build known LaTeX command set from our mapping
    from .formula_extractor import UNICODE_TO_LATEX
    known_cmds = sorted(
        {v.lstrip('\\') for v in UNICODE_TO_LATEX.values()},
        key=len, reverse=True  # longest first for greedy matching
    )

    # Find and pair $ delimiters: $...$ expressions
    # Walk through the string, tracking opening $ positions
    result: list[str] = []
    i = 0
    while i < len(md):
        if md[i] == '$':
            # Look for the matching closing $
            j = i + 1
            while j < len(md):
                if md[j] == '$':
                    # Found closing $ — this is a $...$ expression
                    content = md[i + 1:j]
                    # Strip leading/trailing whitespace
                    content = content.strip()
                    # Fix LaTeX command spacing: add space between a
                    # known command and a directly following letter
                    # (e.g. "\inS" → "\in S") so KaTeX can parse them.
                    # Only add space before UPPERCASE letters to avoid
                    # prefix conflicts: \subseteq won't be split by the
                    # \subset regex because "eq" is lowercase, while
                    # actual variable letters (S, A, X) are uppercase.
                    for cmd in known_cmds:
                        content = re.sub(
                            rf'\\{cmd}([A-Z])',
                            lambda m, c=cmd: '\\' + c + ' ' + m.group(1),
                            content,
                        )
                    result.append('$')
                    result.append(content)
                    result.append('$')
                    i = j + 1
                    break
                j += 1
            else:
                # No closing $ found — output as-is
                result.append(md[i])
                i += 1
        else:
            result.append(md[i])
            i += 1
    return ''.join(result)


def _normalize_whitespace(md: str) -> str:
    """Normalize markdown whitespace.

    Preserves hard-break markers (two trailing spaces on a line) which are
    needed for nested list structures rendered as continuous text blocks.
    """
    # Collapse 3+ newlines to 2
    md = re.sub(r'\n{3,}', '\n\n', md)
    # Remove trailing whitespace per line, but preserve hard-break markers
    # (2+ trailing spaces = intentional hard line break in markdown)
    lines = md.split('\n')
    normalized = []
    for line in lines:
        trailing_len = len(line) - len(line.rstrip())
        stripped = line.rstrip()
        if trailing_len >= 2:
            # Preserve hard break marker (exactly 2 trailing spaces)
            normalized.append(stripped + '  ')
        else:
            normalized.append(stripped)
    md = '\n'.join(normalized)
    # Remove leading newlines
    md = md.lstrip('\n')
    return md


def _hard_breaks(text: str) -> str:
    """Convert single \\n to hard breaks, preserve \\n\\n as paragraph breaks.

    PDF line breaks are deliberate layout decisions. Single \\n (inter-line)
    gets the markdown hard-break marker (two spaces + \\n). Double \\n
    (inter-block paragraph break) stays as \\n\\n so markdown renders it
    as a proper paragraph gap.
    """
    if '\n' not in text:
        return text
    # Preserve \n\n as paragraph breaks — split on them first
    paragraphs = text.split('\n\n')
    processed = []
    for para in paragraphs:
        if '\n' in para:
            lines = para.split('\n')
            processed.append('  \n'.join(lines))
        else:
            processed.append(para)
    return '\n\n'.join(processed)


def _clean_unicode_math(text: str) -> str:
    """Light cleanup for inline math text WITHOUT KaTeX wrapping.

    When OCR didn't produce valid LaTeX, we keep Unicode math symbols as-is
    (Ω, σ, ∅ render correctly in modern browsers without KaTeX). We only
    fix spacing and remove obvious OCR artifacts.
    """
    text = text.strip()
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text
