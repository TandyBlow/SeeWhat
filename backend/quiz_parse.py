"""
Response parsers that normalize raw LLM output into question dicts.
Keyed by question_type via the PARSERS registry.
"""
import json

from quiz_llm import extract_json


# ── Parse helpers ─────────────────────────────────────────────────

def parse_single_choice(raw: str) -> dict:
    parsed = extract_json(raw)
    required = {"question", "options", "correct_index", "explanation"}
    if not all(k in parsed for k in required):
        raise ValueError("LLM response missing required keys for single_choice")
    if not isinstance(parsed["options"], list) or len(parsed["options"]) != 4:
        raise ValueError("Options must be a list of 4 items")
    if not isinstance(parsed["correct_index"], int) or not (0 <= parsed["correct_index"] <= 3):
        raise ValueError("correct_index must be 0-3")
    parsed["question_type"] = "single_choice"
    return parsed


def parse_true_false(raw: str) -> dict:
    parsed = extract_json(raw)
    required = {"question", "correct_index", "explanation"}
    if not all(k in parsed for k in required):
        raise ValueError("LLM response missing required keys for true_false")
    if parsed["correct_index"] not in (0, 1):
        raise ValueError("correct_index must be 0 or 1 for true_false")
    parsed["options"] = json.dumps(["正确", "错误"])
    parsed["question_type"] = "true_false"
    return parsed


def parse_short_answer(raw: str) -> dict:
    parsed = extract_json(raw)
    required = {"question", "reference_answer", "keywords"}
    if not all(k in parsed for k in required):
        raise ValueError("LLM response missing required keys for short_answer")
    if not isinstance(parsed["keywords"], list):
        raise ValueError("keywords must be a list")
    parsed["options"] = json.dumps({
        "reference_answer": parsed["reference_answer"],
        "keywords": parsed["keywords"],
    })
    parsed["correct_index"] = 0
    parsed["explanation"] = parsed.get("explanation", parsed["reference_answer"])
    parsed["question_type"] = "short_answer"
    return parsed


def parse_batch(raw: str) -> list[dict]:
    parsed = extract_json(raw)
    if "questions" not in parsed or not isinstance(parsed["questions"], list):
        raise ValueError("LLM response missing 'questions' list")
    results = []
    for q in parsed["questions"]:
        q_type = q.get("question_type", "single_choice")
        if q_type == "true_false":
            q["options"] = json.dumps(["正确", "错误"])
            if q.get("correct_index") not in (0, 1):
                q["correct_index"] = 0
        elif q_type == "short_answer":
            q["options"] = json.dumps({
                "reference_answer": q.get("reference_answer", ""),
                "keywords": q.get("keywords", []),
            })
            q["correct_index"] = 0
            q["explanation"] = q.get("explanation", q.get("reference_answer", ""))
        else:
            if "options" not in q or not isinstance(q["options"], list):
                raise ValueError(f"Question missing options: {q}")
            q["options"] = json.dumps(q["options"])
            q["question_type"] = "single_choice"
        if "correct_index" not in q:
            q["correct_index"] = 0
        if "explanation" not in q:
            q["explanation"] = ""
        if "difficulty" not in q:
            q["difficulty"] = "medium"
        results.append(q)
    return results


PARSERS = {
    "single_choice": parse_single_choice,
    "true_false": parse_true_false,
    "short_answer": parse_short_answer,
}
