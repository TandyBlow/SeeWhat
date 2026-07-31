"""
DeepSeek API client and LLM JSON-response parsing helpers for the Acacia chat service.
Owns the LLM API environment configuration that raises RuntimeError at import time.
"""
import json
import logging
import os
import re
from typing import List, Dict, Any

import httpx

from file_parser import sanitize_control_chars

logger = logging.getLogger(__name__)


# DeepSeek API configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY 环境变量未设置")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def call_deepseek(messages: List[Dict[str, str]]) -> str:
    """Call DeepSeek API with JSON mode enforced."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _fix_newlines_in_strings(text: str) -> str:
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            result.append(ch)
            continue
        if ch == '\\' and in_string:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch in ('\n', '\r'):
            result.append('\\n')
            continue
        result.append(ch)
    return ''.join(result)


def _find_json_boundary(text: str, opener: str, closer: str) -> tuple | None:
    start = text.find(opener)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return (start, i + 1)
    return None


def parse_json_response(raw: str) -> dict:
    sanitized = sanitize_control_chars(raw)
    try:
        return json.loads(sanitized, strict=False)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", sanitized, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1), strict=False)
        except json.JSONDecodeError:
            pass
    for opener, closer in [("{", "}"), ("[", "]")]:
        boundary = _find_json_boundary(sanitized, opener, closer)
        if boundary is None:
            continue
        start, end = boundary
        candidate = sanitized[start:end]
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            pass
    for opener, closer in [("{", "}"), ("[", "]")]:
        boundary = _find_json_boundary(sanitized, opener, closer)
        if boundary is None:
            continue
        start, end = boundary
        candidate = sanitized[start:end]
        candidate = _fix_newlines_in_strings(candidate)
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            pass
    preview = raw[:500] if len(raw) > 500 else raw
    raise ValueError(f"LLM response is not valid JSON. Raw preview: {preview}")


# Patterns that indicate the AI is describing conversation process rather than knowledge
META_COMMENTARY_PATTERNS = [
    r"AI[通过问说想想到到讲讲]",
    r"用户[通过问说想想到到记答回笔]",
    r"我们讨论",
    r"对话[中过过程程]",
    r"[推推]测[了]?",
    r"似乎.*用户",
    r"[根根]据对话",
    r"我[问说].*用户",
    r"用户[答回]",
    r"笔记中的关键词",
    r"推断用户",
    r"从.*知识树中.*读取",
    r"不是.*知道.*而是.*推测",
    # Correction chain (修正链路) patterns
    r"[修纠][正改].*理解",
    r"[纠纠]正.*之?前.*理解",
    r"先.*以为.*后[来才]",
    r"一开始.*后来.*[纠纠正]",
    r"起初.*后来.*[修纠]",
    r"误解.*[纠纠]正",
    r"原来.*理解.*不对",
    r"以为.*其实.*不[对是]",
    # Third-person perspective patterns
    r"学习者[^\s]{0,3}(?:学会|掌握|认识|理解|知道)",
    r"AI\s*(?:解释|说明|告诉|指出|纠正|引导|通过|根据|询问)",
]


def _filter_meta_commentary(text: str) -> str:
    """Return the text if clean, or empty string if it describes conversation process."""
    if not text or not text.strip():
        return ""
    import re
    for pattern in META_COMMENTARY_PATTERNS:
        if re.search(pattern, text):
            return ""
    return text
