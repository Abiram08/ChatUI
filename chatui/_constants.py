"""
chatui/_constants.py
Shared constants, defaults, and utility functions.
"""
from __future__ import annotations

import os
import re

VERSION = "0.2.0"

MAX_MESSAGE_CHARS = 12_000
MAX_HISTORY_TURNS = 40
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOOL_ROUNDS = 12
MAX_RATE_LIMIT_HITS = 10_000

_PROVIDERS = {
    "anthropic": ("claude-sonnet-4-20250514", None),
    "ollama": ("llama3.2", "http://localhost:11434/v1"),
    "groq": ("llama-3.3-70b-versatile", "https://api.groq.com/openai/v1"),
    "openai": ("gpt-4o-mini", None),
    "echo": ("echo", None),
}

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": None,
}

DEFAULT_SYSTEM = """You are a helpful, thoughtful AI assistant.
Use markdown formatting where appropriate:
- **bold** for key terms
- `code` for inline code
- fenced code blocks with language tags
- bullet points for lists
When you have tools available, use them to answer questions accurately.
Be concise and focused."""

DEFAULT_SYSTEM_SHORT = "You are a helpful assistant."


def _html_esc(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _sanitize_welcome_title(text: str) -> str:
    text = str(text or "")
    text = _html_esc(text)
    text = re.sub(r"&lt;br\s*/?&gt;", "<br>", text, flags=re.IGNORECASE)
    return text


def _no_key_msg(provider: str) -> str:
    from .exceptions import ChatUIMissingKeyError, ChatUIOllamaError

    env = _ENV_KEYS.get(provider)
    if provider == "ollama":
        return str(ChatUIOllamaError())
    if env:
        return str(ChatUIMissingKeyError(provider, env))
    return f"No API key for provider '{provider}'."


def _check_api_key(provider: str, api_key: str | None) -> str | None:
    env_name = _ENV_KEYS.get(provider)
    if not env_name:
        return api_key or "ollama"
    key = api_key or os.getenv(env_name)
    if not key:
        from .exceptions import ChatUIMissingKeyError
        raise ChatUIMissingKeyError(provider, env_name)
    return key
