"""
Shared DeepSeek LLM client for the learning context chain service.
"""
import os
from typing import Dict, Any, List

import httpx


# DeepSeek API configuration (shared with chat_service)
LLM_API_KEY = os.getenv("LLM_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY 环境变量未设置")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def _call_deepseek_raw(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
