"""
Public list-oriented wiki API: article search, related-topics lookup, and
context block formatting for AI prompt injection.
"""
from urllib.parse import quote

from wiki_http import _cache_key, _cache_put, _cached_get, _api_get, _rest_get
from wiki_registry import _get_source


# ── Public API ───────────────────────────────────────────────────────────


def search_wikipedia(query: str, lang: str = "zh", *, source: str | None = None) -> list[dict]:
    """Search a wiki for articles matching a query.

    Returns up to 5 results: [{"title": str, "description": str, "url": str}, ...]
    For Wikipedia sources, falls back to English if the primary language returns nothing.
    """
    if not query or not query.strip():
        return []

    src_id = source or "wikipedia_zh"
    src = _get_source(src_id)
    q = query.strip()
    key = _cache_key("search", q, lang, src_id)
    cached = _cached_get(key)
    if cached:
        return cached.get("results", [])

    fallback_langs = src.get("fallback_langs", [])
    for attempt_lang in (lang, *fallback_langs):
        data = _api_get({
            "action": "opensearch",
            "search": q,
            "limit": 5,
            "format": "json",
        }, source=src_id, lang=attempt_lang)
        if data and len(data) >= 4:
            titles = data[1]
            descriptions = data[2]
            urls = data[3]
            results = [
                {"title": t, "description": d, "url": u}
                for t, d, u in zip(titles, descriptions, urls)
            ]
            if results:
                _cache_put(key, {"results": results})
                return results

    _cache_put(key, {"results": []})
    return []


def get_related_topics(title: str, lang: str = "zh", *, source: str | None = None) -> list[dict]:
    """Get related articles for a topic.

    Returns up to 10 related articles: [{"title", "extract", "url"}, ...]
    Uses REST API for Wikipedia sources; MediaWiki Action API (generator=links) for others.
    """
    if not title or not title.strip():
        return []

    src_id = source or "wikipedia_zh"
    src = _get_source(src_id)
    t = title.strip()
    key = _cache_key("related", t, lang, src_id)
    cached = _cached_get(key)
    if cached is not None:
        if cached.get("_null"):
            return []
        return cached.get("results", [])

    fallback_langs = src.get("fallback_langs", [])

    if src.get("has_rest_api"):
        # ── Wikipedia REST API path ─────────────────────────────────
        for attempt_lang in (lang, *fallback_langs):
            encoded = quote(t, safe="")
            data = _rest_get(f"/page/related/{encoded}", source=src_id, lang=attempt_lang)
            if data and "pages" in data:
                results = []
                for page in data["pages"][:10]:
                    results.append({
                        "title": page.get("title", ""),
                        "extract": page.get("extract", ""),
                        "url": f"https://{attempt_lang}.wikipedia.org/wiki/{quote(page.get('title', ''))}",
                    })
                if results:
                    _cache_put(key, {"results": results})
                    return results
    else:
        # ── MediaWiki Action API path (use page links as proxy) ─────
        data = _api_get({
            "action": "query",
            "generator": "links",
            "gpllimit": 10,
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": t,
            "format": "json",
        }, source=src_id)
        if data and "query" in data:
            pages = data["query"].get("pages", {})
            results = []
            for page_id, page in pages.items():
                page_title = page.get("title", "")
                results.append({
                    "title": page_title,
                    "extract": page.get("extract", ""),
                    "url": f"https://{src['base_url']}{src.get('destination_content_path', '/wiki/')}{quote(page_title)}",
                })
            if results:
                _cache_put(key, {"results": results[:10]})
                return results[:10]

    _cache_put(key, {"_null": True, "results": []})
    return []


def format_wiki_context(summary: dict | None, related: list[dict] | None = None,
                        *, source_label: str = "Wikipedia") -> str:
    """Format wiki data as a structured context block for AI prompt injection.

    Args:
        summary: Result from get_article_summary().
        related: Optional result from get_related_topics().
        source_label: Display name for the wiki source in the header.

    Returns:
        Formatted string ready for injection, or "" if no data.
    """
    if not summary:
        return ""

    lines = [f"【{source_label} 背景知识】"]

    title = summary.get("title", "")
    description = summary.get("description", "")
    extract = summary.get("extract", "")

    if title:
        lines.append(f"主题：{title}")
    if description:
        lines.append(f"简介：{description}")

    if extract:
        # Truncate extract to ~500 chars to keep prompts manageable
        short = extract[:500].strip()
        if len(extract) > 500:
            short += "…"
        lines.append(f"摘要：{short}")

    if related:
        related_names = [r["title"] for r in related[:8] if r.get("title")]
        if related_names:
            lines.append(f"相关主题：{'、'.join(related_names)}")

    return "\n".join(lines)
