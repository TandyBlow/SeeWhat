"""
Background-image pipeline: project/output path constants, file-based
generation lock helpers, and the gpt-image-2 background generator.
"""
import base64
import json as _json
import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger("style_generator")

# ── Background image pipeline ─────────────────────────────────────────────

# Project root and output paths
_PROJECT_ROOT = Path(__file__).parent.parent
_REFERENCE_IMAGE = _PROJECT_ROOT / "background.png"
_BG_OUTPUT_DIR = _PROJECT_ROOT / "frontend" / "public" / "backgrounds" / "ai"
_GENERATING_LOCK_TTL: float = 600.0  # 10 min — stale locks are ignored


def _is_generating(owner_id: str) -> bool:
    """Check if a generation is currently in progress (lock file exists and is fresh)."""
    lock_file = _BG_OUTPUT_DIR / f"{owner_id}.generating"
    if not lock_file.exists():
        return False
    try:
        data = _json.loads(lock_file.read_text())
        started_at = data.get("started_at", 0)
        if time.time() - started_at > _GENERATING_LOCK_TTL:
            try:
                lock_file.unlink()
            except FileNotFoundError:
                pass
            return False
        return True
    except Exception as e:
        logger.warning("Corrupted generation lock file for %s, cleaning up: %s", owner_id, e)
        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass
        return False


def _acquire_generation_lock(owner_id: str) -> bool:
    """Try to acquire the generation lock. Returns False if already locked."""
    if _is_generating(owner_id):
        return False
    _BG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = _BG_OUTPUT_DIR / f"{owner_id}.generating"
    lock_file.write_text(_json.dumps({"started_at": time.time()}))
    return True


def _release_generation_lock(owner_id: str):
    """Release the generation lock."""
    lock_file = _BG_OUTPUT_DIR / f"{owner_id}.generating"
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass


# ── Background image generation ──────────────────────────────────────────

def _generate_background_image(background_prompt: str, owner_id: str, force: bool = False) -> tuple[str | None, str | None]:
    """Generate a styled background image via gpt-image-2 image editing API.

    Uses the reference background.png as base image and applies the style
    prompt to create a unique background. Result is cached by owner_id.

    Args:
        background_prompt: Style description for the background.
        owner_id: User ID for cache key.
        force: If True, regenerate even if cached file exists.

    Returns (url, error) tuple. url is like /api/backgrounds/ai/{owner_id}.png.
    error is a human-readable reason string when generation is skipped/fails.
    """
    api_key = os.getenv("IMAGE_API_KEY")
    api_url = os.getenv("IMAGE_API_URL")
    model = os.getenv("IMAGE_MODEL", "gpt-image-2")

    if not api_key:
        msg = "IMAGE_API_KEY not set on server"
        print(f"[style] {msg}, skipping background generation")
        return None, msg

    if not api_url:
        msg = "IMAGE_API_URL not set on server"
        print(f"[style] {msg}, skipping background generation")
        return None, msg

    if not background_prompt:
        msg = "No backgroundPrompt from LLM"
        print(f"[style] {msg}, skipping background generation")
        return None, msg

    output_path = _BG_OUTPUT_DIR / f"{owner_id}.png"

    # Skip if already generated for this user (unless force=True)
    if not force and output_path.exists():
        print(f"[style] Background image already exists: {output_path}")
        return f"/api/backgrounds/ai/{owner_id}.png", None

    if not _REFERENCE_IMAGE.exists():
        msg = f"Reference image not found: {_REFERENCE_IMAGE}"
        print(f"[style] {msg}")
        return None, msg

    _BG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": f"Bearer {api_key}"}
    full_prompt = f"保持完全相同的构图和结构，改变为{background_prompt}"

    try:
        image_bytes = open(_REFERENCE_IMAGE, "rb").read()
        files = {"image": ("reference.png", image_bytes, "image/png")}
        data = {
            "model": model,
            "prompt": full_prompt,
            "size": "1536x1024",
            "n": "1",
        }

        print(f"[style] Calling gpt-image-2 for {owner_id}: {background_prompt[:80]}...")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(api_url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                msg = f"Image API returned {resp.status_code}: {resp.text[:200]}"
                print(f"[style] gpt-image-2 error {resp.status_code}: {resp.text[:200]}")
                return None, msg

            result = resp.json()
            if "data" in result and len(result["data"]) > 0:
                b64_data = result["data"][0]["b64_json"]
                image_data = base64.b64decode(b64_data)
                with open(output_path, "wb") as f:
                    f.write(image_data)
                print(f"[style] Background image saved: {output_path} ({len(image_data)/1024:.1f} KB)")
                return f"/api/backgrounds/ai/{owner_id}.png", None
            else:
                msg = f"Image API unexpected response: {str(result)[:200]}"
                print(f"[style] gpt-image-2 unexpected response: {str(result)[:200]}")
                return None, msg
    except Exception as e:
        msg = f"Image generation exception: {e}"
        print(f"[style] Background generation failed: {e}")
        return None, msg
