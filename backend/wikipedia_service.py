"""
Multi-source wiki knowledge service for Acacia.
Provides article search, summary fetching, concept verification, and
context formatting for AI prompt injection.

Supports Wikipedia, 萌娘百科, Yugipedia, and any MediaWiki-based wiki
configured in wiki_registry.json.

Uses Wikipedia REST API where available; falls back to MediaWiki Action API.
All calls are cached in-memory with a 1-hour TTL and fail gracefully.
"""
from wiki_article import get_article_summary, verify_concept
from wiki_api import format_wiki_context, get_related_topics, search_wikipedia
from wiki_registry import _get_source, _load_registry, list_sources
