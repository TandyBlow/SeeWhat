"""
Wiki source registry for Acacia.

Loads wiki source config from wiki_registry.json lazily on first access
and resolves source IDs to their config dicts.
"""
import json
import threading
from pathlib import Path


# ── Registry ───────────────────────────────────────────────────────────────

_REGISTRY_PATH = Path(__file__).parent / "wiki_registry.json"
_registry: dict | None = None
_registry_lock = threading.Lock()


def _load_registry() -> dict:
    """Load the wiki source registry lazily on first access."""
    global _registry
    if _registry is not None:
        return _registry
    with _registry_lock:
        if _registry is not None:
            return _registry
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            _registry = json.load(f)
        return _registry


def _get_source(source_id: str | None = None) -> dict:
    """Resolve a source ID to its config dict.

    When source_id is None, returns the registry's default source.
    """
    registry = _load_registry()
    if source_id is None:
        source_id = registry.get("auto_select", {}).get("default_source", "wikipedia_zh")
    src = registry.get("sources", {}).get(source_id)
    if src is None:
        raise ValueError(f"Unknown wiki source: {source_id}")
    return src


def list_sources() -> list[dict]:
    """Return all registered wiki sources with their metadata."""
    registry = _load_registry()
    return [
        {"id": src_id, **cfg}
        for src_id, cfg in registry.get("sources", {}).items()
    ]
