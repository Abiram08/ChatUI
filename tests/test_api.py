"""Tests for the public chat() API."""
from __future__ import annotations

from unittest.mock import MagicMock

from chatui import chat, ChatUI, VERSION


class TestPublicAPI:
    def test_version_is_string(self):
        assert isinstance(VERSION, str)
        assert VERSION == "0.3.0"

    def test_chat_is_callable(self):
        assert callable(chat)

    def test_chat_constructs_and_runs_app(self, monkeypatch):
        run_mock = MagicMock()

        def fake_init(self, **kwargs):
            self.reply = kwargs["reply"]
            self.title = kwargs.get("title", "Chat")

        monkeypatch.setattr(ChatUI, "__init__", fake_init)
        monkeypatch.setattr(ChatUI, "run", run_mock)

        def handler(message, session):
            return "ok"

        result = chat(reply=handler, title="API Test")
        assert result is None
        run_mock.assert_called_once_with()

    def test_chatui_constructs(self):
        app = ChatUI(reply=lambda m, s: "")
        assert isinstance(app, ChatUI)

    def test_chatui_with_all_params(self):
        app = ChatUI(
            reply=lambda m, s: "ok",
            title="Test",
            subtitle="Sub",
            logo="T",
            welcome_title="Welcome",
            layout="sidebar",
            theme="dark",
            chips=["a", "b"],
            host="127.0.0.1",
            port=9000,
        )
        assert app.title == "Test"
        assert app.subtitle == "Sub"
        assert app.logo == "T"
        assert app.layout == "sidebar"
        assert app.theme == "dark"
        assert app.chips == ["a", "b"]

    def test_chatui_reply_function(self):
        def my_reply(msg, session):
            return f"msg: {msg}"

        app = ChatUI(reply=my_reply)
        assert app.reply("hello", {}) == "msg: hello"
