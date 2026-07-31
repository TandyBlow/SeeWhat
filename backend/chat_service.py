"""
Single-topic Socratic chat service for Acacia.
Each node gets its own conversation — AI helps the user understand ONE topic
through natural dialogue, referencing the node's title and any provided material.

This module is now a pure re-export shim; the implementation lives in the
chat_*.py modules it imports from below.
"""
from chat_llm import call_deepseek, parse_json_response
from chat_knowledge import _get_node_content_tail
from chat_enrichment_post import _refresh_response_concepts
from chat_knowledge_profile import build_knowledge_profile
from chat_session_mark import detect_abbreviation_name, mark_concept_node
from chat_start import start_chat
from chat_turn import process_chat_turn
from chat_regenerate import regenerate_with_tree_context
from chat_session import end_chat, get_chat_session, get_active_session_by_node
from chat_compress import compress_chat_session
