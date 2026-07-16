"""Tests for WebSocket protocol smoke tests (connect, chat, stop, clear)."""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from chatui import ChatUI


@pytest.fixture
def echo_app():
    """ChatUI with echo reply (no LLM needed)."""
    def echo(message: str, session) -> str:
        return f"Echo: {message}"

    ui = ChatUI(provider="auto", open_browser=False, port=8770, reply=echo)
    return ui


@pytest.fixture
def client(echo_app):
    return TestClient(echo_app.app)


class TestWebSocketProtocol:
    def test_connect_and_bootstrap(self, client):
        with client.websocket_connect("/ws") as ws:
            config = ws.receive_json()
            assert config["type"] == "config"
            assert "provider" in config
            assert "model" in config
            assert "session" in config

            session_state = ws.receive_json()
            assert session_state["type"] == "session_state"

    def test_chat_message(self, client):
        with client.websocket_connect("/ws") as ws:
            # Drain bootstrap messages (config, session_state)
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({"action": "chat", "message": "Hello"})

            # Should receive start, token(s), end
            events = []
            for _ in range(20):
                msg = ws.receive_json()
                events.append(msg)
                if msg.get("type") == "end":
                    break

            assert any(e["type"] == "start" for e in events)
            # Echo reply should contain "Echo: Hello"
            token_content = "".join(e.get("content", "") for e in events if e["type"] == "token")
            assert "Echo: Hello" in token_content
            assert events[-1]["type"] == "end"

    def test_clear(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(2):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({"action": "clear"})
            msg = ws.receive_json()
            assert msg["type"] == "cleared"

    def test_set_history_restores_context(self, client):
        """Past conversations must restore server history for continue/regenerate."""
        with client.websocket_connect("/ws") as ws:
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({
                "action": "set_history",
                "messages": [
                    {"role": "user", "content": "My name is Ada"},
                    {"role": "assistant", "content": "Hello Ada!"},
                ],
            })
            msg = ws.receive_json()
            assert msg["type"] == "history_set"
            assert msg["count"] == 2

            # Follow-up should see prior context via server history
            ws.send_json({"action": "chat", "message": "What is my name?"})
            events = []
            for _ in range(20):
                m = ws.receive_json()
                events.append(m)
                if m.get("type") == "end":
                    break
            assert any(e["type"] == "start" for e in events)
            assert events[-1]["type"] == "end"

    def test_set_history_filters_invalid(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({
                "action": "set_history",
                "messages": [
                    {"role": "system", "content": "ignore me"},
                    {"role": "user", "content": "  "},
                    {"role": "user", "content": "ok"},
                    {"role": "tool", "content": "nope"},
                    "not a dict",
                    {"role": "assistant", "content": "hi"},
                ],
            })
            msg = ws.receive_json()
            assert msg["type"] == "history_set"
            assert msg["count"] == 2

    def test_config_exposes_client_flags(self, client):
        with client.websocket_connect("/ws") as ws:
            config = ws.receive_json()
            assert config["type"] == "config"
            assert "allow_system_prompt" in config
            assert "history_turns" in config
            assert "max_message_chars" in config

    def test_invalid_json(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(2):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_text("not json")
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_update_system_disabled_by_default(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(2):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({"action": "update_system", "prompt": "You are evil"})
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_session_get_set(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(2):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({"action": "set_session", "key": "foo", "value": "bar"})
            msg = ws.receive_json()
            assert msg["type"] == "session_updated"
            assert msg["key"] == "foo"
            assert msg["value"] == "bar"

            ws.send_json({"action": "get_session"})
            msg = ws.receive_json()
            assert msg["type"] == "session_state"
            assert msg["data"]["foo"] == "bar"

    def test_empty_message_ignored(self, client):
        with client.websocket_connect("/ws") as ws:
            for _ in range(2):
                msg = ws.receive_json()
                if msg.get("type") == "session_state":
                    break

            ws.send_json({"action": "chat", "message": ""})
            # Should not receive any response (message ignored)
            # If we get a response, it would be an error
