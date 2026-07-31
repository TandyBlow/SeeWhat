"""
Low-level HTTP transport for wiki sources.

In-memory cache with a 1-hour TTL, per-source rate limiter, and HTTP GET
helpers for both the Wikipedia REST and MediaWiki Action APIs.
"""
import hashlib
import threading
import time
from typing import Dict

import httpx

from wiki_registry import _get_source


# ── Cache ────────────────────────────────────────────────────────────────

_wiki_cache: Dict[str, dict] = {}
_cache_ttl: float = 3600.0  # 1 hour


def _cache_key(op: str, title: str, lang: str, source: str) -> str:
    return hashlib.sha256(f"{op}|{source}|{lang}|{title}".encode("utf-8")).hexdigest()


def _cached_get(key: str) -> dict | None:
    entry = _wiki_cache.get(key)
    if entry and (time.time() - entry.get("_cached_at", 0)) < _cache_ttl:
        return entry
    return None


def _cache_put(key: str, data: dict) -> None:
    data["_cached_at"] = time.time()
    _wiki_cache[key] = data


# ── Rate limiter ──────────────────────────────────────────────────────────

_last_request: dict[str, float] = {}
_rate_lock = threading.Lock()


def _rate_limit(source_id: str, min_interval: float) -> None:
    """Enforce a minimum interval between requests to a source."""
    if min_interval <= 0:
        return
    with _rate_lock:
        last = _last_request.get(source_id, 0)
        elapsed = time.time() - last
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _last_request[source_id] = time.time()


# ── HTTP helpers ───────────────────────────────────────────────────────────

USER_AGENT = "Acacia/1.0 (knowledge-app; https://github.com/acacia)"


def _rest_get(path: str, source: str = "wikipedia_zh", lang: str | None = None,
              timeout: float = 10.0) -> dict | None:
    """GET a Wikipedia REST endpoint. Returns parsed JSON or None on failure."""
    src = _get_source(source)
    base = src["base_url"]
    if lang and src.get("has_rest_api"):
        parts = base.split(".", 1)
        if len(parts) == 2:
            base = f"{lang}.{parts[1]}"
    url = f"https://{base}{src['rest_path']}{path}"
    ua = src.get("user_agent") or USER_AGENT
    headers = {"User-Agent": ua, "Accept": "application/json"}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        return None


def _api_get(params: dict, source: str = "wikipedia_zh", lang: str | None = None,
             timeout: float = 10.0) -> dict | None:
    """GET a MediaWiki Action API endpoint. Returns parsed JSON or None on failure."""
    src = _get_source(source)
    base = src["base_url"]
    if lang and src.get("has_rest_api"):
        parts = base.split(".", 1)
        if len(parts) == 2:
            base = f"{lang}.{parts[1]}"
    url = f"https://{base}{src['api_path']}"
    ua = src.get("user_agent") or USER_AGENT
    headers = {"User-Agent": ua, "Accept": "application/json"}
    _rate_limit(source, src.get("rate_limit", 0))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        return None
