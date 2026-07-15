"""
chatui/exceptions.py
Custom exception hierarchy for clear, copy-paste-friendly errors.
"""
from __future__ import annotations

import sys


class ChatUIError(Exception):
    """Base class for all ChatUI errors."""


class ChatUINoProviderError(ChatUIError):
    """No LLM provider detected from environment variables."""

    def __init__(self) -> None:
        is_win = sys.platform == "win32"
        set_cmd = "$env:{key} = 'your-key-here'" if is_win else 'export {key}="your-key-here"'
        msg = (
            "No LLM provider found. Set one of:\n\n"
            f"  # Groq (fastest, free tier)\n  {set_cmd.format(key='GROQ_API_KEY')}\n\n"
            f"  # OpenAI\n  {set_cmd.format(key='OPENAI_API_KEY')}\n\n"
            f"  # Anthropic\n  {set_cmd.format(key='ANTHROPIC_API_KEY')}\n\n"
            "  # Ollama (local, no key needed — just run: ollama serve)\n\n"
            "Then run: chatui"
        )
        super().__init__(msg)


class ChatUIMissingKeyError(ChatUIError):
    """Provider requires an API key but none is set."""

    def __init__(self, provider: str, key_name: str) -> None:
        is_win = sys.platform == "win32"
        if is_win:
            export = f"$env:{key_name} = 'your-key-here'"
        else:
            export = f'export {key_name}="your-key-here"'
        super().__init__(
            f"Missing {key_name} for provider '{provider}'.\n\n"
            f"  {export}\n\n"
            "Then restart your app."
        )


class ChatUIOllamaError(ChatUIError):
    """Cannot connect to Ollama."""

    def __init__(self) -> None:
        super().__init__(
            "Cannot connect to Ollama at http://localhost:11434\n\n"
            "  Is Ollama running? Start it with:\n"
            "    ollama serve\n\n"
            "  Then pull a model:\n"
            "    ollama pull llama3.2"
        )


class ChatUIProviderError(ChatUIError):
    """Provider-specific runtime error (e.g. API failure)."""


class ChatUIRegistrationError(ChatUIError):
    """Duplicate tool, component, or handler name."""

    def __init__(self, kind: str, name: str) -> None:
        super().__init__(f"{kind} '{name}' is already registered")


__all__ = [
    "ChatUIError",
    "ChatUINoProviderError",
    "ChatUIMissingKeyError",
    "ChatUIOllamaError",
    "ChatUIProviderError",
    "ChatUIRegistrationError",
]
