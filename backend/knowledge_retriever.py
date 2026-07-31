"""
Knowledge retriever for line-by-line chat mode.
Indexes user knowledge point contents and searches for matches against
extracted atomic concepts. Returns structured personalized context.

Split into knowledge_index (index construction) and knowledge_search (search/present).
"""
from knowledge_index import (
    build_content_index,
    KnowledgeIndex,
    _tokenize,
    _describe_match,
    _TOKEN_RE,
)
from knowledge_search import (
    search_user_knowledge,
    format_personalized_context,
    get_user_kp_names,
)
