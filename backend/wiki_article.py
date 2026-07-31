"""
Public article-centric wiki API: single-article summary fetch and
concept verification built on the summary.
"""
from urllib.parse import quote

from wiki_http import _cache_key, _cache_put, _cached_get, _api_get, _rest_get
from wiki_registry import _get_source


# ── Public API ───────────────────────────────────────────────────────────


def get_article_summary(title: str, lang: str = "zh", *, source: str | None = None) -> dict | None:
    """Get a wiki article summary.

    Returns {"title", "extract", "description", "url", "thumbnail", "source_name", "source_id"} or None.
    The extract is a plain-text summary (usually 2-4 paragraphs).

    Uses REST API for Wikipedia sources; MediaWiki Action API for others.
    """
    if not title or not title.strip():
        return None

    src_id = source or "wikipedia_zh"
    src = _get_source(src_id)
    t = title.strip()
    key = _cache_key("summary", t, lang, src_id)
    cached = _cached_get(key)
    if cached is not None:
        if cached.get("_null"):
            return None
        return cached

    fallback_langs = src.get("fallback_langs", [])

    if src.get("has_rest_api"):
        # ── Wikipedia REST API path ─────────────────────────────────
        for attempt_lang in (lang, *fallback_langs):
            encoded = quote(t, safe="")
            data = _rest_get(f"/page/summary/{encoded}", source=src_id, lang=attempt_lang)
            if data and data.get("title") != "Not found.":
                result = {
                    "title": data.get("title", t),
                    "extract": data.get("extract", ""),
                    "description": data.get("description", ""),
                    "url": f"https://{attempt_lang}.wikipedia.org/wiki/{quote(t)}",
                    "thumbnail": data.get("thumbnail", {}).get("source", ""),
                    "lang": attempt_lang,
                    "source_name": src.get("name", "Wikipedia"),
                    "source_id": src_id,
                }
                _cache_put(key, result)
                return result
    else:
        # ── MediaWiki Action API path (non-Wikipedia wikis) ────────
        data = _api_get({
            "action": "query",
            "prop": "extracts|pageimages|info",
            "exintro": 1,
            "explaintext": 1,
            "piprop": "thumbnail",
            "pithumbsize": 300,
            "inprop": "url",
            "titles": t,
            "format": "json",
        }, source=src_id)
        if data and "query" in data:
            pages = data["query"].get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue  # page not found
                result = {
                    "title": page.get("title", t),
                    "extract": page.get("extract", ""),
                    "description": "",
                    "url": f"https://{src['base_url']}{src.get('destination_content_path', '/wiki/')}{quote(page.get('title', t))}",
                    "thumbnail": page.get("thumbnail", {}).get("source", ""),
                    "lang": src.get("default_lang", lang),
                    "source_name": src.get("name", "Wikipedia"),
                    "source_id": src_id,
                }
                _cache_put(key, result)
                return result

    # Cache the miss
    _cache_put(key, {"_null": True})
    return None


def verify_concept(name: str, lang: str = "zh", *, source: str | None = None) -> dict:
    """Check if a term has a wiki article.

    Returns {"verified": bool, "title": str, "summary": str, "description": str, "url": str}.
    Tries the primary language first, falls back to configured fallback languages.
    """
    summary = get_article_summary(name, lang, source=source)
    if summary:
        return {
            "verified": True,
            "title": summary["title"],
            "summary": summary["extract"],
            "description": summary.get("description", ""),
            "url": summary.get("url", ""),
        }
    return {
        "verified": False,
        "title": name,
        "summary": "",
        "description": "",
        "url": "",
    }
