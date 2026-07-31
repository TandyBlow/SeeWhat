"""
Wikipedia verification and concept deduplication filters used by both the
pre-response and post-response enrichment pipelines.
"""
import logging
import re
import sys

logger = logging.getLogger(__name__)


def _verify_concepts_via_wikipedia(concepts: list, log_prefix: str = "[WIKI]", source_text: str = "") -> list:
    """Verify each concept against Wikipedia and attach verification fields.

    Concepts without Wikipedia articles are normally filtered out, BUT
    domain-specific concepts that are substantially discussed may be kept
    even without Wikipedia coverage. The bar is intentionally high to avoid
    extracting generic words or passing example mentions as knowledge points.
    On API failure, concepts are kept unverified (graceful degradation).
    """
    import sys
    if not concepts:
        return []
    try:
        from wikipedia_service import verify_concept
    except ImportError:
        print(f"{log_prefix} wikipedia_service not available, keeping all {len(concepts)} concepts", file=sys.stderr)
        for c in concepts:
            c["verified"] = False
            c["wiki_summary"] = ""
            c["wiki_description"] = ""
        return concepts

    # Count how many times each concept name appears in the source text
    mention_counts = {}
    if source_text:
        for c in concepts:
            name = c.get("name", "")
            if name and len(name) >= 2:
                mention_counts[name] = source_text.count(name)

    verified = []
    for c in concepts:
        name = c.get("name", "")
        if not name or len(name) < 2:
            continue
        try:
            vc = verify_concept(name)
            if vc.get("verified"):
                c["verified"] = True
                c["wiki_summary"] = vc.get("summary", "")
                c["wiki_description"] = vc.get("description", "")
                verified.append(c)
                print(f"{log_prefix} ✓ {name}", file=sys.stderr)
            else:
                # For non-Wikipedia concepts, require stronger evidence that this
                # is a genuine domain concept, not a generic word or passing mention.
                mentions = mention_counts.get(name, 0)
                definition = c.get("definition", "")
                category = c.get("category", "")

                # Require BOTH: mentioned 3+ times AND has a substantive definition
                if mentions >= 3 and len(definition) >= 20:
                    c["verified"] = False
                    c["wiki_summary"] = ""
                    c["wiki_description"] = ""
                    verified.append(c)
                    print(f"{log_prefix} ~ {name} (no Wikipedia, mentioned {mentions}x, substantive def — kept)", file=sys.stderr)
                elif mentions >= 3:
                    print(f"{log_prefix} ✗ {name} (no Wikipedia, mentioned {mentions}x but def too short ({len(definition)} chars))", file=sys.stderr)
                elif len(definition) >= 20:
                    print(f"{log_prefix} ✗ {name} (no Wikipedia, substantive def but only {mentions} mention(s))", file=sys.stderr)
                else:
                    print(f"{log_prefix} ✗ {name} (no Wikipedia, only {mentions} mention(s), short def)", file=sys.stderr)
        except Exception as e:
            logger.warning("%s wikipedia verify failed for '%s': %s", log_prefix, c.get("name", "?"), e)
            c["verified"] = False
            c["wiki_summary"] = ""
            c["wiki_description"] = ""
            verified.append(c)

    print(f"{log_prefix} verified {len(verified)}/{len(concepts)} concepts", file=sys.stderr)
    return verified


def _deduplicate_concepts(concepts: list, log_prefix: str = "[DEDUP]") -> list:
    """Merge near-duplicate concepts based on name overlap.

    Handles cases like:
    - Substring: "人才" is wholly contained in "人才管理" → merge, keep longer
    - Shared prefix/suffix: "光荣公司" vs "光荣特库摩" share "光荣" → merge, keep more formal
    - Character overlap >= 66% of the shorter name → merge
    """
    import sys
    if len(concepts) <= 1:
        return concepts

    def _norm(s: str) -> str:
        """Strip common suffixes for comparison."""
        import re
        s = s.strip()
        s = re.sub(r'[（(][^)）]*[)）]', '', s)  # remove parentheticals
        return s

    merged = []
    used = [False] * len(concepts)

    for i, ci in enumerate(concepts):
        if used[i]:
            continue
        name_i = ci.get("name", "")
        if not name_i:
            used[i] = True
            continue

        best = ci
        best_name = name_i
        best_idx = i

        for j, cj in enumerate(concepts):
            if i == j or used[j]:
                continue
            name_j = cj.get("name", "")
            if not name_j:
                used[j] = True
                continue

            # Check substring relationship
            if name_i in name_j or name_j in name_i:
                # Keep the longer, more formal version
                if len(name_j) > len(best_name):
                    best = cj
                    best_name = name_j
                    best_idx = j
                    used[i] = True
                else:
                    used[j] = True
                continue

            # Check character overlap
            norm_i = _norm(name_i)
            norm_j = _norm(name_j)
            if len(norm_i) >= 2 and len(norm_j) >= 2:
                common = sum(1 for ch in norm_i if ch in norm_j)
                shorter_len = min(len(norm_i), len(norm_j))
                if common >= shorter_len * 0.66:
                    # Merge: keep the more formal (longer) name
                    if len(name_j) > len(best_name):
                        best = cj
                        best_name = name_j
                        best_idx = j
                        used[i] = True
                    else:
                        used[j] = True

        # Merge definitions if we're keeping a different concept than ci
        if best_idx != i:
            # Add mention of the merged name in definition if it's different enough
            old_def = best.get("definition", "")
            other_name = name_i
            if other_name not in old_def and other_name not in best_name:
                if old_def:
                    best["definition"] = f"{old_def}（也称{other_name}）"
            print(f"{log_prefix} merged '{name_i}' → '{best_name}'", file=sys.stderr)

        merged.append(best)
        if best_idx != i:
            used[i] = True
        used[best_idx] = True

    return merged
