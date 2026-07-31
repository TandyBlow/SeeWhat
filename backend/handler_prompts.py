"""
Narrow handler prompt templates for the refactored chat architecture.
Shim module — implementation split into:
  - prompt_line_by_line.py:    line-by-line mode system + builders
  - prompt_socratic.py:       single-topic Socratic system + builders
  - prompt_knowledge_gap.py:  knowledge-gap handler system + builder
"""
from prompt_line_by_line import LINE_BY_LINE_EXPLAIN_SYSTEM
from prompt_line_by_line import LINE_BY_LINE_ANSWER_SYSTEM
from prompt_line_by_line import build_line_by_line_explain_prompt
from prompt_line_by_line import build_line_by_line_answer_prompt
from prompt_socratic import SOCRATIC_GENERATE_QUESTION_SYSTEM
from prompt_socratic import SOCRATIC_END_SYSTEM
from prompt_socratic import build_socratic_question_prompt
from prompt_socratic import build_socratic_evaluate_prompt
from prompt_socratic import build_socratic_end_prompt
from prompt_knowledge_gap import KNOWLEDGE_GAP_SUGGEST_SYSTEM
from prompt_knowledge_gap import build_knowledge_gap_prompt
