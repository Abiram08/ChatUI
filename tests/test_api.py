"""Tests for chat() API and provider auto-detection."""
from __future__ import annotations

import os
from unittest.mock import patch
import pytest
from chatui.api import chat
from chatui.app import ChatUI
from chatui.exceptions import ChatUINoProviderError


class TestProviderDetection:
    def test_detect_groq(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from chatui.providers.detect import detect_provider_from_env

        provider, model = detect_provider_from_env()
        assert provider == "groq"
        assert "llama" in model

    def test_detect_openai(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        from chatui.providers.detect import detect_provider_from_env

        provider, model = detect_provider_from_env()
        assert provider == "openai"

    def test_detect_anthropic(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from chatui.providers.detect import detect_provider_from_env

        provider, model = detect_provider_from_env()
        assert provider == "anthropic"

    def test_no_provider_raises(self, monkeypatch):
        for key in ("GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        from chatui.providers.detect import detect_provider_from_env

        with pytest.raises(ChatUINoProviderError):
            detect_provider_from_env()

    def test_no_provider_error_message_has_bash_export(self, monkeypatch):
        for key in ("GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        try:
            from chatui.providers.detect import detect_provider_from_env

            detect_provider_from_env()
        except ChatUINoProviderError as e:
            msg = str(e)
            assert "GROQ_API_KEY" in msg
            assert "export" in msg or "$env:" in msg

    def test_auto_provider_skips_detection_with_reply(self):
        """When reply is provided, auto-detection should be skipped."""
        app = ChatUI(
            provider="auto",
            open_browser=False,
            reply=lambda msg, sess: f"Echo: {msg}",
        )
        assert app._reply_fn is not None
        assert app._client is None
        assert app.provider == "echo"


class TestChatAPI:
    def test_chat_function_exists(self):
        assert callable(chat)

    def test_chat_function_signature(self):
        import inspect

        sig = inspect.signature(chat)
        params = set(sig.parameters.keys())
        assert "tools" in params
        assert "components" in params
        assert "on" in params
        assert "reply" in params
        assert "title" in params
        assert "theme" in params
        assert "provider" in params


class TestFromEnv:
    def test_from_env_classmethod(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        app = ChatUI.from_env(open_browser=False)
        assert app.provider == "groq"

    def test_asgi_method(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        app = ChatUI.from_env(open_browser=False)
        asgi_app = app.asgi()
        assert asgi_app is not None

    def test_mount_method(self, monkeypatch):
        from fastapi import FastAPI

        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        parent = FastAPI()
        chat_app = ChatUI.from_env(open_browser=False)
        chat_app.mount(parent, "/chat")
