"""
Learning Context Chain service for Acacia.
Tracks user navigation across knowledge points and builds contextual
awareness for AI-generated adaptive openings.
"""
from context_chain_llm import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    _call_deepseek_raw,
)
from context_chain_opening import (
    ADAPTIVE_OPENING_SYSTEM,
    _fallback_opening,
    generate_adaptive_opening,
    logger,
)
from context_chain_summary import (
    LEARNING_SUMMARY_SYSTEM,
    generate_learning_summary,
)
from context_chain_transitions import (
    _node_name,
    build_transition_context_text,
    get_chain_to_node,
    get_new_learnings_since_last_visit,
    get_recent_transitions,
    record_learning_snapshot,
    record_transition,
)
