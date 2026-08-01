"""Tests for the WebSocket chat endpoint."""
from __future__ import annotations

import pytest
from chatui import ChatUI


@pytest.mark.asyncio
async def test_ws_connect_and_chat():
    app = ChatUI(reply=lambda m, s: f"You said: {m}", title="WSTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        config = ws.receive_json()
        assert config["type"] == "config"
        assert "chatui" in config["label"]

        ws.send_json({"action": "chat", "message": "hello"})

        msg = ws.receive_json()
        assert msg["type"] == "start"

        msg = ws.receive_json()
        assert msg["type"] == "token"
        assert "You said: hello" in msg["content"]

        msg = ws.receive_json()
        assert msg["type"] == "end"


@pytest.mark.asyncio
async def test_ws_clear_session():
    app = ChatUI(reply=lambda m, s: f"session: {s}", title="ClearTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "clear"})
        ws.send_json({"action": "chat", "message": "test"})
        ws.receive_json()
        resp = ws.receive_json()
        assert resp["type"] == "token"


@pytest.mark.asyncio
async def test_ws_empty_message():
    app = ChatUI(reply=lambda m, s: "", title="EmptyTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": ""})
        msg = ws.receive_json()
        assert msg["type"] == "start"
        msg = ws.receive_json()
        assert msg["type"] == "end"


@pytest.mark.asyncio
async def test_ws_handler_error():
    def failing(m, s):
        raise ValueError("handler error")

    app = ChatUI(reply=failing, title="ErrorTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": "hi"})
        msg = ws.receive_json()
        assert msg["type"] == "start"
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "handler error" in msg["content"]
        msg = ws.receive_json()
        assert msg["type"] == "end"


@pytest.mark.asyncio
async def test_ws_set_history_is_applied_to_session():
    def reply(message, session):
        return f"history-count: {len(session.get('history', []))}"

    app = ChatUI(reply=reply, title="HistoryTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "set_history",
                "messages": [
                    {"role": "user", "content": "u1"},
                    {"role": "assistant", "content": "a1"},
                ],
            }
        )
        ws.send_json({"action": "chat", "message": "u2"})
        assert ws.receive_json()["type"] == "start"
        token = ws.receive_json()
        assert token["type"] == "token"
        assert "history-count: 3" in token["content"]
        assert ws.receive_json()["type"] == "end"


@pytest.mark.asyncio
async def test_ws_chat_appends_assistant_message_to_history():
    def reply(message, session):
        history = session.get("history", [])
        for item in reversed(history):
            if item.get("role") == "assistant":
                return f"last: {item.get('content', '')}"
        return f"echo: {message}"

    app = ChatUI(reply=reply, title="HistoryAppendTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": "first"})
        assert ws.receive_json()["type"] == "start"
        ws.receive_json()
        assert ws.receive_json()["type"] == "end"

        ws.send_json({"action": "chat", "message": "second"})
        assert ws.receive_json()["type"] == "start"
        token = ws.receive_json()
        assert token["type"] == "token"
        assert token["content"] == "last: echo: first"
        assert ws.receive_json()["type"] == "end"
