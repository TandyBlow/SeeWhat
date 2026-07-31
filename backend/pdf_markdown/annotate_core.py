"""
Shared module-level state and low-level LLM transport for structural annotation.

Holds the logging singleton, API config constants read from env at import
time, LLM JSON response parsing, and the exponential-backoff HTTP call.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

import httpx

logger = logging.getLogger(__name__)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = 60.0
MAX_RETRIES = 3
BASE_DELAY = 1.0


def _parse_llm_json(raw: str) -> dict | None:
    """Parse LLM response as JSON with fallback strategies."""
    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract from markdown code fence
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find outermost { } pair
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def call_llm_with_retry(
    messages: list[dict],
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    json_mode: bool = True,
) -> str:
    """Call LLM with exponential backoff. Raises RuntimeError on exhaustion."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, read=LLM_TIMEOUT)) as client:
                resp = client.post(
                    f"{LLM_BASE_URL}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException, ValueError) as e:
            last_error = e
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"LLM call failed after {max_retries} retries: {last_error}"
                ) from last_error
            # Fast bail: if connection-level error (SSL, DNS, refused),
            # don't waste time retrying — server is likely down
            if isinstance(e, httpx.ConnectError):
                raise RuntimeError(
                    f"LLM server unreachable, aborting: {e}"
                ) from e
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                f"retrying in {delay:.1f}s: {e}"
            )
            time.sleep(delay)

    raise RuntimeError(f"LLM call failed: {last_error}")
