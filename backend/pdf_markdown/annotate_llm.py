"""
LLM prompt layer for structural annotation.

The system prompt template, chunk text formatting for LLM consumption, and
label-range validation against the real document text.
"""

from __future__ import annotations

from .annotation_schema import StructuralLabel, LabeledSpan, SentenceAnnotation
from .annotate_core import logger

ANNOTATION_SYSTEM_PROMPT = """You are a document structure annotator. Your task is to label character ranges in text with structural types.

CRITICAL RULE: You MUST NOT generate, modify, rephrase, or create any text. You ONLY output character position ranges that point to EXISTING text in the input. Think of yourself as a highlighter pen — you mark what's already there.

## Labels you can assign:

- **heading_1**: Document title (usually just one)
- **heading_2**: Major section heading
- **heading_3**: Sub-section heading
- **heading_4**: Sub-sub-section heading
- **ordered_list_item**: Part of a numbered/lettered list (1., 2., a., b., i., ii., etc.)
- **unordered_list_item**: Part of a bulleted list (•, -, * items)
- **blockquote**: Quoted or specially highlighted text
- **math**: Inline mathematical expression that should be wrapped in $...$. This includes single variables when used in mathematical context (e.g., "S" in "a set S is in F")
- **display_math**: Block-level displayed equation that should be wrapped in $$...$$
- **code_block**: Monospace code listing
- **paragraph**: Normal body text (default type)

## Rules:

1. Every visible text character must belong to exactly ONE label. Use "paragraph" as the default.
2. char_start is INCLUSIVE, char_end is EXCLUSIVE. The range must exactly match the input text.
3. For headings: level must be consistent. No skipping levels (h2→h4 without h3 is invalid). The heading label should cover the heading TEXT only, NOT the leading whitespace or trailing newline.
4. For ordered_list_item: nesting_level starts at 1. Sub-items get level 2, 3, etc. The label MUST cover the entire item INCLUDING the bullet/number prefix (e.g., "(a) Sample space Ω" is one label, not split into "(a)" + "Sample space Ω"). This ensures the prefix is preserved in the output.
5. For unordered_list_item: same nesting rule as ordered.
6. For math: ANY mathematical expression including single-letter variables in context (e.g., "S" in mathematical discussion), operators, Greek letters, formulas. Override italic for math variables — label them math not paragraph.
7. For display_math: large centered equations, multi-line derivations, anything that stands alone as a formula block.
8. Short standalone lines that look like titles should be headings (check content, not length).
9. Sentences that are purely punctuation or whitespace can be omitted from the output.
10. Nested ordered lists (like "(a)", "(b)" under a numbered item) are separate list items with higher nesting_level.

## NESTED LIST DETECTION — CRITICAL:

Many academic documents use hierarchical list structures like:

1. Probability space
   (a) Sample space Ω
   (b) Event
   (c) σ-algebra F

Or:

(a) Sample space Ω:
    i. all BNBU students
    ii. in a medical diagnosis
    iii. we assume Ω to be finite

In these cases:
- The top-level numbered items (1., 2., etc.) are ordered_list_item with nesting_level=1
- Lettered sub-items ((a), (b), (c)) are ordered_list_item with nesting_level=2
- Roman numeral sub-items (i., ii., iii.) are ordered_list_item with nesting_level=3

EACH sub-item MUST be labeled as its own ordered_list_item range, NOT merged into a paragraph. For example, "(a) Sample space Ω" should be one ordered_list_item (nesting=2) that INCLUDES the "(a)" prefix, "i. all BNBU students" should be a separate ordered_list_item (nesting=3) that INCLUDES the "i." prefix, etc.

NEVER label nested list items as "paragraph" — always use ordered_list_item with the correct nesting_level.

## EXAMPLE ITEMS IN LIST HIERARCHIES — CRITICAL:

Academic documents often include "Example 1:", "Example 2:", "Definition:", etc. within list hierarchies. These are NOT standalone paragraphs — they belong to the parent list structure and must be labeled as list items with the correct nesting.

For example, in this structure:

  (c) σ-algebra F on sample space:
    i. The empty set ∅ is in F
    ii. The union of any set in F is also in F
    iii. If a set S is in F, the complement Sc is also in F
    Example 1: rolling a six-sided dice...
    Example 2: consider a sample space Ω= {a, b, c}...

The "Example 1" and "Example 2" items should be labeled as unordered_list_item with nesting_level=3 (same depth as i., ii., iii.), NOT as paragraph.

Similarly, "Definition:", "Remark:", "Note:" items inside list hierarchies should be labeled as unordered_list_item at the same nesting level as their sibling list items.

NEVER label "Example N:", "Definition:", "Remark:", or "Note:" items as "paragraph" when they appear within a list structure.

## Output JSON format:
{
  "sentences": [
    {
      "sentence_id": <int>,
      "char_start": <int>,
      "char_end": <int>,
      "labels": [
        {
          "label": "<one of the label types above>",
          "char_start": <int>,
          "char_end": <int>,
          "nesting_level": <int>,
          "confidence": <float 0.0-1.0>
        }
      ]
    }
  ]
}

OUTPUT ONLY VALID JSON. No markdown fences, no explanations, no other text."""


def _format_chunk_for_llm(segments) -> str:
    """Format a chunk of segments as numbered text with character positions."""
    lines: list[str] = []
    for seg in segments:
        lines.append(f"[S{seg.sentence_id} | chars {seg.char_start}-{seg.char_end}]")
        # Show context if present
        if seg.context_before:
            lines.append(f"  context_before: {repr(seg.context_before[:200])}")
        lines.append(f"  text: {repr(seg.text)}")
        if seg.context_after:
            lines.append(f"  context_after: {repr(seg.context_after[:200])}")
        lines.append("")
    return "\n".join(lines)


def _validate_annotation(
    sent: SentenceAnnotation,
    full_text: str,
) -> SentenceAnnotation:
    """Validate and fix annotation positions against the actual text.

    Discards labels whose char_start/char_end don't match the text content.
    Falls back to 'paragraph' for invalid labels.
    """
    validated: list[LabeledSpan] = []

    for label in sent.labels:
        if label.char_start < 0 or label.char_end > len(full_text):
            logger.warning(
                f"S{sent.sentence_id}: label {label.label.value} "
                f"[{label.char_start}:{label.char_end}] out of bounds, discarding"
            )
            continue
        if label.char_start >= label.char_end:
            logger.warning(
                f"S{sent.sentence_id}: label {label.label.value} has empty range, discarding"
            )
            continue

        # Verify text slice exists
        sliced = full_text[label.char_start:label.char_end]
        if not sliced.strip():
            logger.warning(
                f"S{sent.sentence_id}: label {label.label.value} covers only whitespace, discarding"
            )
            continue

        validated.append(label)

    if not validated:
        # Fall back to paragraph for the sentence range
        validated.append(LabeledSpan(
            label=StructuralLabel.PARAGRAPH,
            char_start=sent.char_start,
            char_end=sent.char_end,
            confidence=0.0,
        ))

    sent.labels = validated
    return sent
