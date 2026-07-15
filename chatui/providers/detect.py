"""
chatui/providers/detect.py
Auto-detect provider from environment variables.
"""
from __future__ import annotations

import os

from ..exceptions import ChatUINoProviderError

_PROVIDER_PRIORITY = [
    ("groq", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    ("openai", "OPENAI_API_KEY", "gpt-4o-mini"),
    ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
]

_OLLAMA_MODEL = "llama3.2"
_OLLAMA_URL = "http://localhost:11434"


def detect_provider_from_env() -> tuple[str, str]:
    """
    Auto-detect provider from environment variables.

    Returns (provider_name, model_name). Raises ChatUINoProviderError if none found.
    """
    for provider, env_key, model in _PROVIDER_PRIORITY:
        if os.environ.get(env_key):
            return provider, model

    # Try Ollama
    try:
        import httpx

        r = httpx.get(f"{_OLLAMA_URL}/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama", _OLLAMA_MODEL
    except Exception:
        pass

    raise ChatUINoProviderError()
