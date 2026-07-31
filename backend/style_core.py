"""
Public style-generation orchestrator: the generate_style entry point plus
the default-fallback response helper.
"""
import logging
import time

from style_cache import (
    _bg_image_cache,
    _cache_key,
    _cache_ttl,
    _populate_background,
    _should_regenerate,
    _style_cache,
    build_profile_text,
)
from style_color import DEFAULT_PARAMS, _validate_params
from style_llm import STYLE_SYSTEM_PROMPT, _call_deepseek, _parse_json
from style_image import (
    _BG_OUTPUT_DIR,
    _acquire_generation_lock,
    _generate_background_image,
    _is_generating,
    _release_generation_lock,
)

logger = logging.getLogger("style_generator")

# ── Public API ────────────────────────────────────────────────────────────

def _default_style_response(distribution: dict | None = None) -> dict:
    """Default fallback style response when AI generation is skipped/fails."""
    return {
        "style": "default",
        "params": DEFAULT_PARAMS,
        "backgroundPrompt": "",
        "backgroundUrl": None,
        "distribution": distribution or {},
    }


def generate_style(owner_id: str, nodes: list[dict], force: bool = False) -> dict:
    """Generate a unique visual style for a user's knowledge tree.

    Args:
        owner_id: The user's ID (used for cache key).
        nodes: List of node dicts with 'name' and 'content' keys.
        force: If True, bypass cache and regenerate.

    Returns:
        {"style": "styleName", "params": {...}, "backgroundPrompt": "...",
         "distribution": {...}}

    IMPORTANT: This function blocks until background image generation completes.
    The returned style is fully ready to apply (params + background image).
    """
    # If another request is already generating for this user, tell the client to poll.
    # Wrapped defensively — lock check failure must never crash the endpoint.
    try:
        if _is_generating(owner_id):
            return {"generating": True}
    except Exception as e:
        print(f"[style] WARNING: _is_generating failed for {owner_id}: {e}")

    if not nodes:
        return _default_style_response()

    # Require at least 10 nodes for meaningful AI style generation
    if len(nodes) < 10:
        return _default_style_response()

    # Build profile text for cache key and prompt
    profile_text = build_profile_text(nodes)

    # Check cache
    cache_key = _cache_key(profile_text)
    if not force:
        cached = _style_cache.get(cache_key)
        if cached and (time.time() - cached.get("_cached_at", 0)) < _cache_ttl:
            # Ensure backgroundUrl is populated (may be None if bg gen failed previously)
            if cached.get("backgroundUrl") is None:
                _populate_background(cached, cache_key, owner_id, "Retrying background image generation for cached style")
            return cached

    # Check if regeneration is warranted (cooldown + change detection)
    if not force and not _should_regenerate(owner_id, profile_text):
        # Return cached result even if TTL expired, or fall back to default
        cached = _style_cache.get(cache_key)
        if cached:
            if cached.get("backgroundUrl") is None:
                _populate_background(cached, cache_key, owner_id, "Retrying background image for cached style")
            return cached
        # Cache miss: image may exist on disk from an interrupted previous request.
        # Recover it so the user doesn't lose a successfully generated background.
        image_path = _BG_OUTPUT_DIR / f"{owner_id}.png"
        if image_path.exists():
            print(f"[style] Recovering background image from disk for {owner_id}")
            recovered = {
                "style": "default",
                "params": DEFAULT_PARAMS,
                "backgroundPrompt": "",
                "backgroundUrl": f"/api/backgrounds/ai/{owner_id}.png",
                "distribution": {},
                "_cached_at": time.time(),
            }
            _style_cache[cache_key] = recovered
            return recovered
        return _default_style_response()

    # Build user prompt
    user_lines = []
    for n in nodes:
        name = n.get("name", "")
        content = (n.get("content") or "")[:300]
        if content:
            user_lines.append(f"- {name}: {content}")
        else:
            user_lines.append(f"- {name}")
    user_prompt = "以下是一个学习者的知识库内容，请分析其知识世界的气质与情感温度，生成匹配的视觉风格参数：\n\n" + "\n".join(user_lines)

    # Compute domain distribution for backward compat
    domain_counts: dict[str, int] = {}
    for n in nodes:
        tag = n.get("domain_tag") or "其他"
        domain_counts[tag] = domain_counts.get(tag, 0) + 1
    total = len(nodes)
    distribution = {tag: round(cnt / total, 4) for tag, cnt in domain_counts.items()}

    # Acquire generation lock so concurrent requests poll instead of racing.
    # Wrapped defensively — lock failure must never block generation.
    try:
        locked = _acquire_generation_lock(owner_id)
    except Exception as e:
        print(f"[style] WARNING: _acquire_generation_lock failed for {owner_id}: {e}")
        locked = True  # Proceed without lock if the mechanism is broken
    if not locked:
        return {"generating": True}

    try:
        # Call DeepSeek
        print(f"[style] Generating style for {owner_id} with {len(nodes)} nodes...")
        try:
            raw = _call_deepseek([
                {"role": "system", "content": STYLE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            result = _parse_json(raw)
            print(f"[style] DeepSeek returned style: {result.get('styleName', 'unknown')}")
        except Exception as e:
            logger.error("[style] DeepSeek call failed: %s", e)
            # Fallback to default
            return _default_style_response(distribution)

        style_name = result.get("styleName", "default")
        description = result.get("styleDescription", "")
        background_prompt = result.get("backgroundPrompt", "")
        params = _validate_params(result.get("params", {}))

        # Generate background image via gpt-image-2 (BLOCKS until complete)
        print(f"[style] Generating background image for {owner_id} (force={force})...")
        background_url, bg_error = _generate_background_image(background_prompt, owner_id, force=force)
        if background_url:
            print(f"[style] Background image ready: {background_url}")
        else:
            print(f"[style] Background image generation failed or skipped: {bg_error}")
        _bg_image_cache[cache_key] = background_url

        output = {
            "style": style_name,
            "styleDescription": description,
            "params": params,
            "backgroundPrompt": background_prompt,
            "backgroundUrl": background_url,
            "distribution": distribution,
            "_cached_at": time.time(),
        }
        if bg_error:
            output["bgError"] = bg_error

        _style_cache[cache_key] = output
        print(f"[style] Style generation complete for {owner_id}")
        return output
    finally:
        _release_generation_lock(owner_id)
