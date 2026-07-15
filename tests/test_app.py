"""Tests for ChatUI app class — builder client, providers, edge cases."""
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock
from chatui.app import ChatUI
from chatui.exceptions import ChatUIRegistrationError


class TestChatUIInit:
    def test_default_provider_fallback(self):
        app = ChatUI(provider="auto", open_browser=False, reply=lambda m, s: "ok")
        assert app.provider == "echo"
        assert app._reply_fn is not None

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ChatUI(provider="nonsense", open_browser=False)

    def test_theme_defaults_to_valid(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        assert app.theme == "manuscript"

    def test_invalid_theme_falls_back(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok",
                     theme="nonexistent")
        assert app.theme == "manuscript"

    def test_lite_mode(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok",
                     lite=True)
        assert app.lite is True

    def test_history_turns_default(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        assert app.history_turns == 40

    def test_custom_history_turns(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok",
                     history_turns=10)
        assert app.history_turns == 10

    def test_allow_client_system_prompt(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok",
                     allow_client_system_prompt=True)
        assert app.allow_client_system_prompt is True

    def test_themes_subset(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok",
                     themes=["ink", "manuscript"])
        assert app._themes_subset == ["ink", "manuscript"]


class TestRegistration:
    def test_duplicate_tool_raises(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        def my_tool():
            return "ok"
        app.register_tool(my_tool)
        with pytest.raises(ChatUIRegistrationError):
            app.register_tool(my_tool)

    def test_duplicate_component_raises(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        def my_comp(data):
            return "<div></div>"
        app.register_component("test", my_comp)
        with pytest.raises(ChatUIRegistrationError):
            app.register_component("test", my_comp)

    def test_add_tools_accepts_list(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        def a():
            pass

        def b():
            pass
        app.add_tools([a, b])
        assert "a" in app._registry.names()
        assert "b" in app._registry.names()

    def test_add_tools_accepts_dict(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        def fn():
            pass
        app.add_tools({"renamed": fn})
        assert "renamed" in app._registry.names()

    def test_handler_separate_keys(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        def h1(data):
            pass

        def h2(data):
            pass
        app.register_handler("event_a", h1)
        app.register_handler("event_b", h2)
        assert len(app._on_handlers["event_a"]) == 1
        assert len(app._on_handlers["event_b"]) == 1


class TestClientBuilder:
    def test_build_anthropic_client_no_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        app = ChatUI(provider="anthropic", open_browser=False)
        # Without key, client will be None
        assert app._client is None

    def test_build_ollama_client(self):
        app = ChatUI(provider="ollama", open_browser=False)
        assert app._client is not None

    def test_build_groq_client(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        app = ChatUI(provider="groq", open_browser=False)
        assert app._client is not None

    def test_build_openai_client(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        app = ChatUI(provider="openai", open_browser=False)
        assert app._client is not None


class TestFromEnvMount:
    def test_from_env_with_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        app = ChatUI.from_env(open_browser=False)
        assert app.provider == "groq"

    def test_mount_into_parent(self):
        from fastapi import FastAPI

        parent = FastAPI()
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        app.mount(parent, "/chat")
        # Mounted app should have routes
        routes = [r.path for r in parent.routes]
        assert any("/chat" in r for r in routes)

    def test_asgi_returns_app(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        asgi_app = app.asgi()
        assert asgi_app is not None


class TestHooks:
    @pytest.mark.asyncio
    async def test_on_token_hook(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        tokens = []

        @app.on_token
        def hook(text):
            tokens.append(text)

        await app._run_hooks("on_token", "Hello")
        assert tokens == ["Hello"]

    @pytest.mark.asyncio
    async def test_on_tool_hook(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        calls = []

        @app.on_tool
        def hook(name, inputs):
            calls.append((name, inputs))

        await app._run_hooks("on_tool", "search", {"q": "test"})
        assert calls == [("search", {"q": "test"})]

    @pytest.mark.asyncio
    async def test_on_error_hook(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        errors = []

        @app.on_error
        def hook(msg):
            errors.append(msg)

        await app._run_hooks("on_error", "Something broke")
        assert errors == ["Something broke"]

    @pytest.mark.asyncio
    async def test_on_end_hook(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        usages = []

        @app.on_end
        def hook(usage):
            usages.append(usage)

        await app._run_hooks("on_end", {"input": 10, "output": 5})
        assert usages == [{"input": 10, "output": 5}]

    @pytest.mark.asyncio
    async def test_async_hook(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")
        tokens = []

        @app.on_token
        async def hook(text):
            tokens.append(text)

        await app._run_hooks("on_token", "async works")
        assert tokens == ["async works"]

    @pytest.mark.asyncio
    async def test_hook_error_does_not_propagate(self):
        app = ChatUI(provider="echo", open_browser=False, reply=lambda m, s: "ok")

        @app.on_token
        def failing(text):
            raise ValueError("hook failed")

        @app.on_token
        def ok(text):
            pass

        await app._run_hooks("on_token", "test")
        # Should not raise
