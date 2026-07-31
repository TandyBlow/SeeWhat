"""Text-content rule checks for structural annotations.

Layer 1 deterministic checks that scan the raw text: character
coverage/overlap, mid-word boundary integrity, and the natural-language
vs code_block heuristic. Self-contained; imports nothing from the other
review_* modules.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, SentenceAnnotation, RuleViolation


def _check_interval_coverage(
    annotations: list[SentenceAnnotation],
    text: str,
) -> list[RuleViolation]:
    """Check that all characters are covered and no labels overlap."""
    violations: list[RuleViolation] = []
    text_len = len(text)

    # Track which characters are claimed by labels
    coverage: dict[int, int] = {}  # char_pos → number of labels claiming it

    for sent_ann in annotations:
        for label in sent_ann.labels:
            for i in range(label.char_start, min(label.char_end, text_len)):
                coverage[i] = coverage.get(i, 0) + 1

    # Check for overlaps (multiple labels claiming same character)
    overlap_starts: list[int] = []
    for i in sorted(coverage.keys()):
        if coverage[i] > 1:
            if not overlap_starts or i > overlap_starts[-1] + 1:
                overlap_starts.append(i)

    for start in overlap_starts:
        end = start
        while end + 1 in coverage and coverage[end + 1] > 1:
            end += 1
        violations.append(RuleViolation(
            region=(start, end + 1),
            rule_name="INTERVAL_OVERLAP",
            severity="error",
            description=f"Characters {start}-{end + 1} claimed by {coverage[start]} labels",
        ))

    # Check for gaps (no label claiming a visible character)
    gap_starts: list[int] = []
    for i in range(text_len):
        if text[i].strip() and i not in coverage:
            if not gap_starts or i > gap_starts[-1] + 1:
                gap_starts.append(i)

    for start in gap_starts[:5]:  # Cap to avoid flooding
        end = start
        while end + 1 < text_len and end + 1 not in coverage and text[end + 1].strip():
            end += 1
        violations.append(RuleViolation(
            region=(start, end + 1),
            rule_name="INTERVAL_GAP",
            severity="warning",
            description=f"Characters {start}-{end + 1} not covered by any label",
        ))

    return violations


def _check_boundary_integrity(
    annotations: list[SentenceAnnotation],
    text: str,
) -> list[RuleViolation]:
    """Check that label boundaries don't split mid-word."""
    violations: list[RuleViolation] = []

    for sent_ann in annotations:
        for label in sent_ann.labels:
            start = label.char_start
            end = label.char_end

            # Check start: is it at a whitespace boundary or sentence start?
            if start > 0 and text[start - 1].isalnum() and text[start].isalnum():
                # Label starts mid-word — look backward to find word start
                word_start = start - 1
                while word_start > 0 and text[word_start - 1].isalnum():
                    word_start -= 1
                violations.append(RuleViolation(
                    region=(word_start, end),
                    rule_name="BOUNDARY_MID_WORD_START",
                    severity="warning",
                    description=f"Label starts mid-word at position {start}",
                ))

            # Check end: is it at a whitespace boundary or sentence end?
            if end < len(text) and text[end - 1].isalnum() and end < len(text) and text[end].isalnum():
                word_end = end
                while word_end < len(text) and text[word_end].isalnum():
                    word_end += 1
                violations.append(RuleViolation(
                    region=(start, word_end),
                    rule_name="BOUNDARY_MID_WORD_END",
                    severity="warning",
                    description=f"Label ends mid-word at position {end}",
                ))

    return violations


# Common English words for natural language detection
_COMMON_WORDS = frozenset({
    "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "may", "might", "shall", "should",
    "and", "but", "or", "nor", "not", "so", "yet", "for",
    "if", "then", "than", "that", "this", "these", "those",
    "a", "an", "of", "in", "on", "at", "to", "from", "by",
    "with", "about", "into", "through", "during", "before",
    "after", "above", "below", "between", "under", "over",
    "we", "you", "they", "it", "he", "she", "me", "us",
    "also", "because", "since", "while", "although", "however",
    "therefore", "thus", "hence", "moreover", "furthermore",
    "example", "definition", "remark", "note", "case", "proof",
    "theorem", "lemma", "corollary", "proposition",
})


def _check_false_code_blocks(
    annotations: list[SentenceAnnotation],
    text: str,
) -> list[RuleViolation]:
    """Detect code_block labels covering natural language, not actual code.

    Math-heavy academic paragraphs sometimes get mislabeled as code_block
    because they contain symbols and notation. A genuine code block should
    contain programming constructs (function definitions, variable assignments,
    loop structures) rather than English sentences and mathematical prose.
    """
    violations: list[RuleViolation] = []

    for sent_ann in annotations:
        for label in sent_ann.labels:
            if label.label != StructuralLabel.CODE_BLOCK:
                continue

            # Extract the labeled text
            if label.char_end > len(text):
                continue
            block_text = text[label.char_start:label.char_end]

            # Count common English words in the block
            words = block_text.lower().split()
            common_count = sum(1 for w in words if w.rstrip(".,;:!?") in _COMMON_WORDS)
            word_ratio = common_count / max(len(words), 1)

            # Heuristic: if >15% of words are common English words and the block
            # has >6 words, it's very likely natural language, not code
            if len(words) > 6 and word_ratio > 0.15:
                violations.append(RuleViolation(
                    region=(label.char_start, label.char_end),
                    rule_name="FALSE_CODE_BLOCK",
                    severity="error",
                    description=(
                        f"code_block label covers natural language text "
                        f"(common-word ratio {word_ratio:.0%}, {common_count}/{len(words)} words)"
                    ),
                ))

    return violations
