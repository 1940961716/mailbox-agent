from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

_LAST_LLM_ERROR = ""


def get_last_llm_error() -> str:
    return _LAST_LLM_ERROR


def _extract_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _post_chat_completion(base_url: str, api_key: str, body: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_openai_compatible(system: str, user: str) -> dict[str, Any] | None:
    global _LAST_LLM_ERROR
    _LAST_LLM_ERROR = ""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        _LAST_LLM_ERROR = "LLM_API_KEY/OPENAI_API_KEY is not configured; rule fallback was used."
        return None
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        try:
            data = _post_chat_completion(base_url, api_key, body)
        except Exception as first_exc:
            fallback_body = dict(body)
            fallback_body.pop("response_format", None)
            data = _post_chat_completion(base_url, api_key, fallback_body)
            _LAST_LLM_ERROR = f"response_format retry: {type(first_exc).__name__}: {first_exc}"
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        parsed.setdefault("_llm_provider", base_url)
        parsed.setdefault("_llm_model", model)
        if _LAST_LLM_ERROR:
            parsed.setdefault("_llm_warning", _LAST_LLM_ERROR)
            _LAST_LLM_ERROR = ""
        return parsed
    except Exception as exc:
        _LAST_LLM_ERROR = f"{type(exc).__name__}: {exc}"
        return None
