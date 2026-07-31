"""
AI quiz question generation service — SQLite variant.
Supports single_choice, true_false, short_answer, and batch generation.
All generated questions are persisted to quiz_questions table.
"""
from quiz_llm import (
    BATCH_PROMPT,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    PROMPTS,
    SHORT_ANSWER_PROMPT,
    SINGLE_CHOICE_PROMPT,
    TRUE_FALSE_PROMPT,
    call_llm,
    extract_json,
    _find_json_boundary,
)
from quiz_parse import (
    PARSERS,
    parse_batch,
    parse_short_answer,
    parse_single_choice,
    parse_true_false,
)
from quiz_sqlite import (
    TYPE_LABELS,
    _collect_node_content,
    _node_to_input,
    _persist_question,
    generate_batch_questions_sqlite,
    generate_quiz_question_sqlite,
)
from quiz_answers import compute_adaptive_difficulty, submit_quiz_answer_sqlite
from quiz_stats import (
    get_questions_by_node_sqlite,
    get_quiz_stats_sqlite,
    get_single_question_sqlite,
    get_wrong_questions_sqlite,
)
