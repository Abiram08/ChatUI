"""Tests for streaming reply handlers (sync/async generators)."""
from __future__ import annotations

from typing import AsyncGenerator, Generator

import pytest
from chatui import ChatUI


@pytest.mark.asyncio
async def test_sync_generator_streams():
    def gen_reply(message: str, session: dict) -> Generator[str, None, None]:
        for word in message.split():
            yield f"{word} "

    app = ChatUI(reply=gen_reply, title="GenTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": "hello world"})
        assert ws.receive_json()["type"] == "start"
        tokens = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "end":
                break
            if msg["type"] == "token":
                tokens.append(msg["content"])
        assert len(tokens) >= 2


@pytest.mark.asyncio
async def test_async_generator_streams():
    async def async_gen_reply(message: str, session: dict) -> AsyncGenerator[str, None]:
        for ch in message:
            yield ch.upper()
            await asyncio.sleep(0)

    import asyncio
    app = ChatUI(reply=async_gen_reply, title="AsyncGenTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": "abc"})
        assert ws.receive_json()["type"] == "start"
        tokens = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "end":
                break
            if msg["type"] == "token":
                tokens.append(msg["content"])
        assert len(tokens) >= 3


@pytest.mark.asyncio
async def test_async_function_returns_string():
    async def async_reply(message: str, session: dict) -> str:
        return f"async: {message}"

    app = ChatUI(reply=async_reply, title="AsyncTest")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"action": "chat", "message": "hello"})
        assert ws.receive_json()["type"] == "start"
        msg = ws.receive_json()
        assert msg["type"] == "token"
        assert "async: hello" in msg["content"]
        assert ws.receive_json()["type"] == "end"
