"""
Knowledge index construction for line-by-line chat mode.
Tokenizer, the KnowledgeIndex class (add/search with Jaccard similarity),
the why-description helper, and build_content_index which loads user nodes
via a function-local import.
"""
import re


# ── Simple tokenizer (no external dependencies) ──────────────────────────

# Common Chinese + English word boundary patterns
_TOKEN_RE = re.compile(r'[一-鿿]+|[a-zA-Z0-9_]+|[^\s]')


def _tokenize(text: str) -> set:
    """Tokenize text into a set of normalized tokens.

    Handles mixed Chinese/English text without external dependencies.
    Chinese characters are treated as individual tokens for substring matching;
    English words are kept as-is.
    """
    if not text:
        return set()
    text = text.lower().strip()
    tokens = set()
    # Chinese chars as individual tokens
    chinese = re.findall(r'[一-鿿]', text)
    tokens.update(chinese)
    # English/identifier words
    english = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
    tokens.update(w.lower() for w in english)
    # Numbers
    numbers = re.findall(r'\d+', text)
    tokens.update(numbers)
    return tokens


# ── Knowledge Index ──────────────────────────────────────────────────────


class KnowledgeIndex:
    """A simple searchable index of user knowledge point contents."""

    def __init__(self):
        self.entries: list[dict] = []  # [{kp_id, kp_name, content, tokens}]

    def add(self, kp_id: str, kp_name: str, content: str):
        """Add a knowledge point to the index."""
        self.entries.append({
            "kp_id": kp_id,
            "kp_name": kp_name,
            "content": content,
            "tokens": _tokenize(content) | _tokenize(kp_name),
        })

    def search(self, concept: dict, threshold: float = 0.10) -> list[dict]:
        """Search the index for matches against a concept.

        Args:
            concept: A dict with 'name', 'definition', 'category' keys.
            threshold: Minimum Jaccard similarity to consider a match.

        Returns:
            List of matches, each with {kp_name, content_snippet, score, why}.
            Empty list if no matches above threshold.
        """
        # Build query tokens from concept name + definition
        query_text = concept.get("name", "") + " " + concept.get("definition", "")
        query_tokens = _tokenize(query_text)

        if not query_tokens:
            return []

        matches = []
        for entry in self.entries:
            entry_tokens = entry["tokens"]
            if not entry_tokens:
                continue

            # Jaccard similarity
            intersection = len(query_tokens & entry_tokens)
            union = len(query_tokens | entry_tokens)
            if union == 0:
                continue
            score = intersection / union

            if score >= threshold:
                snippet = entry["content"][:200] if entry["content"] else ""
                matches.append({
                    "kp_name": entry["kp_name"],
                    "content_snippet": snippet,
                    "score": score,
                    "why": _describe_match(concept, entry, score),
                })

        # Sort by score descending, return top 5
        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches[:5]


def _describe_match(concept: dict, entry: dict, score: float) -> str:
    """Build a brief description of why this match is relevant."""
    concept_name = concept.get("name", "")
    kp_name = entry["kp_name"]
    if score > 0.3:
        return f"用户对「{kp_name}」的理解与当前知识点「{concept_name}」有明确关联"
    elif score > 0.15:
        return f"「{kp_name}」与「{concept_name}」部分相关"
    return f"「{kp_name}」可能涉及「{concept_name}」的某些方面"


# ── Public API ───────────────────────────────────────────────────────────


def build_content_index(owner_id: str) -> KnowledgeIndex:
    """Build a searchable content index from all user knowledge points.

    Args:
        owner_id: The user's ID.

    Returns:
        KnowledgeIndex with all user KP contents indexed.
    """
    from tree_repository_sqlite import fetch_user_nodes_with_knowledge

    index = KnowledgeIndex()
    nodes = fetch_user_nodes_with_knowledge(owner_id)
    for node in nodes:
        content = node.get("content", "") or ""
        name = node.get("name", "")
        kp_id = node.get("id", "")
        if name:  # Only index nodes that have a name
            index.add(kp_id, name, content)
    return index
