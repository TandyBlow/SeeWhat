"""
In-memory style caches, per-user regeneration state, and backgroundUrl
backfill helpers shared across the style generator modules.

Owns all shared mutable dicts (_style_cache, _bg_image_cache, _user_state)
so every other module imports the SAME object identities.
"""
import hashlib
import time

from style_image import _BG_OUTPUT_DIR, _generate_background_image

# ── Cache ────────────────────────────────────────────────────────────────

_style_cache: dict[str, dict] = {}
_cache_ttl: float = 3600.0  # 1 hour

# Background image cache: maps cache_key -> backgroundUrl
_bg_image_cache: dict[str, str] = {}

# Per-user generation state: owner_id -> {"hash": str, "generated_at": float}
_user_state: dict[str, dict] = {}
_MIN_REGENERATE_INTERVAL: float = 300.0  # 5 min cooldown between AI generations

# Jaccard similarity threshold for triggering regeneration.
# When the profile text changes, we compute Jaccard similarity on character
# bigrams between old and new text. Only trigger regeneration if similarity
# drops below this threshold — meaning the knowledge structure has changed
# substantially, not just a typo fix or single-node addition.
_JACCARD_THRESHOLD: float = 0.80


def _cache_key(nodes_json: str) -> str:
    return hashlib.sha256(nodes_json.encode("utf-8")).hexdigest()


def build_profile_text(nodes: list[dict]) -> str:
    """Build a stable, content-based profile text from node data."""
    profile_parts = []
    for n in nodes:
        name = n.get("name", "")
        content = (n.get("content") or "")[:200]
        profile_parts.append(f"{name}:{content}")
    return "|".join(sorted(profile_parts))


def _bigrams(text: str) -> set[str]:
    """Extract character bigrams from text for Jaccard similarity."""
    return {text[i:i+2] for i in range(len(text) - 1)} if len(text) >= 2 else set()


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity on character bigrams between two texts."""
    bg_a = _bigrams(text_a)
    bg_b = _bigrams(text_b)
    if not bg_a and not bg_b:
        return 1.0
    if not bg_a or not bg_b:
        return 0.0
    intersection = bg_a & bg_b
    union = bg_a | bg_b
    return len(intersection) / len(union)


def _should_regenerate(owner_id: str, profile_text: str) -> bool:
    """Check whether style should be regenerated for this user.

    Uses Jaccard similarity on character bigrams to detect *substantial*
    changes in the knowledge profile, rather than triggering on every
    single-character edit.

    Returns False if: node count < 10, Jaccard similarity >= threshold
    (content hasn't changed substantially), or within cooldown period.
    Returns True otherwise and updates state.
    """
    state = _user_state.get(owner_id)

    # First time — only trigger AI generation, don't require similarity check
    if not state:
        now = time.time()
        _user_state[owner_id] = {"profile_text": profile_text, "generated_at": now}
        return True

    now = time.time()
    if (now - state["generated_at"]) < _MIN_REGENERATE_INTERVAL:
        return False  # Within cooldown

    prev_text = state.get("profile_text", "")
    if not prev_text:
        _user_state[owner_id] = {"profile_text": profile_text, "generated_at": now}
        return True

    similarity = _jaccard_similarity(prev_text, profile_text)
    print(f"[style] Jaccard similarity: {similarity:.4f} (threshold={_JACCARD_THRESHOLD})")

    if similarity >= _JACCARD_THRESHOLD:
        return False  # Change too small

    _user_state[owner_id] = {"profile_text": profile_text, "generated_at": now}
    return True


def hydrate_user_state(owner_id: str, profile_text: str, generated_at: float = 0.0):
    """Restore per-user state from persistent storage after server restart."""
    _user_state[owner_id] = {"profile_text": profile_text, "generated_at": generated_at}


def cache_style(key: str, result: dict):
    """Store a style result in the in-memory cache from an external source."""
    if "_cached_at" not in result:
        result["_cached_at"] = time.time()
    _style_cache[key] = result


def _populate_background(result: dict, cache_key: str, owner_id: str, retry_message: str):
    """Backfill backgroundUrl into a cached style result.

    Checks the in-memory bg cache, then disk (in case the server restarted),
    then retries background generation if a prompt is available but no image.
    """
    if result.get("backgroundUrl") is not None:
        return
    result["backgroundUrl"] = _bg_image_cache.get(cache_key)
    # Last resort: check disk in case server restarted and cache lost
    if result["backgroundUrl"] is None:
        image_path = _BG_OUTPUT_DIR / f"{owner_id}.png"
        if image_path.exists():
            result["backgroundUrl"] = f"/api/backgrounds/ai/{owner_id}.png"
    # If we have a prompt but still no image, retry generation
    if result.get("backgroundUrl") is None and result.get("backgroundPrompt"):
        print(f"[style] {retry_message} of {owner_id}")
        retry_url, _ = _generate_background_image(result["backgroundPrompt"], owner_id, force=False)
        if retry_url:
            result["backgroundUrl"] = retry_url
            _bg_image_cache[cache_key] = retry_url
