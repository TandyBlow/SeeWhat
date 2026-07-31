"""
LLM infrastructure for AI quiz generation — DeepSeek API client and prompt templates.
Holds the LLM_API_KEY import-time guard and the PROMPTS registry.
"""
import json
import os
import re

import httpx

from file_parser import sanitize_control_chars

LLM_API_KEY = os.getenv("LLM_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY 环境变量未设置")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ── Prompt templates ──────────────────────────────────────────────

SINGLE_CHOICE_PROMPT = (
    "你是一个出题助手。根据用户提供的知识点，生成一道单选题。"
    "只返回JSON，格式为："
    '{"question": "题干", "options": ["A选项", "B选项", "C选项", "D选项"], "correct_index": 0, "explanation": "解析"}'
    "correct_index是正确答案在options里的下标，从0开始。"
    "题目要考察对知识点的真正理解，不能直接照抄原文。"
)

TRUE_FALSE_PROMPT = (
    "你是一个出题助手。根据用户提供的知识点，生成一道判断题。"
    "题目为一个陈述句，用户判断其正确或错误。"
    "只返回JSON，格式为："
    '{"question": "陈述句", "correct_index": 0, "explanation": "解析"}'
    "correct_index: 0表示该陈述正确，1表示该陈述错误。"
    "陈述句不能过于显而易见，要有一定的迷惑性。"
)

SHORT_ANSWER_PROMPT = (
    "你是一个出题助手。根据用户提供的知识点，生成一道简答题。"
    "只返回JSON，格式为："
    '{"question": "题目", "reference_answer": "参考答案要点", "keywords": ["关键词1", "关键词2"]}'
    "题目要求用户用自己的话回答，不能太宽泛也不能太琐碎。"
)

BATCH_PROMPT = (
    "你是一个出题助手。根据用户提供的知识点集合，生成{count}道{type_desc}。"
    "只返回JSON，格式为："
    '{"questions": [{"question": "...", "options": [...], "correct_index": 0, "explanation": "...", "question_type": "..."}]}'
    "题目要考察对知识点的真正理解，不能直接照抄原文。"
    "尽量覆盖不同知识点，不要所有题目都针对同一个知识点。"
)


# ── LLM helpers ───────────────────────────────────────────────────

def call_llm(user_input: str, system_prompt: str, temperature: float = 0.8) -> str:
    if not LLM_API_KEY:
        raise ValueError("未配置LLM_API_KEY环境变量，无法调用AI服务")
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _find_json_boundary(text: str, opener: str, closer: str) -> tuple | None:
    """Find outermost JSON object/array boundary, skipping string contents."""
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


def extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and malformed responses."""
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

    preview = raw[:500] if len(raw) > 500 else raw
    raise ValueError(f"LLM response is not valid JSON. Raw response preview: {preview}")


PROMPTS = {
    "single_choice": SINGLE_CHOICE_PROMPT,
    "true_false": TRUE_FALSE_PROMPT,
    "short_answer": SHORT_ANSWER_PROMPT,
}
