"""Tests for WebSocket handler internals (handle_websocket, _loop_reply, _rate_ok, _handle_widget_event)."""
from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from chatui import ChatUI
from chatui._constants import VERSION, MAX_MESSAGE_CHARS
from chatui.server.ws import _rate_ok, _loop_reply, _handle_widget_event
from chatui.runtime.connection import ConnectionState


class TestRateOk:
    @pytest.mark.asyncio
    async def test_no_limiter(self):
        app = MagicMock()
        app._rate_limiter = None
        assert await _rate_ok(app, "127.0.0.1", AsyncMock()) is True

    @pytest.mark.asyncio
    async def test_under_limit(self):
        app = MagicMock()
        limiter = MagicMock()
        limiter.check.return_value = True
        app._rate_limiter = limiter
        assert await _rate_ok(app, "127.0.0.1", AsyncMock()) is True

    @pytest.mark.asyncio
    async def test_over_limit_sends_error(self):
        app = MagicMock()
        limiter = MagicMock()
        limiter.check.return_value = False
        app._rate_limiter = limiter
        send = AsyncMock()
        result = await _rate_ok(app, "127.0.0.1", send)
        assert result is False
        send.assert_called_once()
        assert send.call_args[0][0]["type"] == "error"


class TestLoopReply:
    @pytest.mark.asyncio
    async def test_sync_reply_string(self):
        app = MagicMock()
        app._reply_fn = lambda msg, sess: f"Echo: {msg}"
        app._emit_handler_result = AsyncMock()
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        await _loop_reply(app, conn, "hello", send)
        start_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "start"]
        token_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "token"]
        end_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "end"]
        assert len(start_msgs) == 1
        assert len(token_msgs) == 1
        assert token_msgs[0][0][0]["content"] == "Echo: hello"
        assert len(end_msgs) == 1

    @pytest.mark.asyncio
    async def test_sync_reply_widgets(self):
        from chatui import metric

        app = MagicMock()
        app._emit_handler_result = AsyncMock()
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()

        def reply_fn(msg, sess):
            return metric("Test", "123")
        app._reply_fn = reply_fn

        await _loop_reply(app, conn, "show", send)
        assert app._emit_handler_result.called

    @pytest.mark.asyncio
    async def test_async_reply(self):
        async def async_reply(msg, sess):
            return f"Async: {msg}"

        app = MagicMock()
        app._reply_fn = async_reply
        app._emit_handler_result = AsyncMock()
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        await _loop_reply(app, conn, "test", send)
        token_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "token"]
        assert any("Async: test" in c[0][0].get("content", "") for c in token_msgs)

    @pytest.mark.asyncio
    async def test_async_gen_reply(self):
        async def gen_reply(msg, sess):
            yield "chunk1"
            yield "chunk2"

        app = MagicMock()
        app._reply_fn = gen_reply
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        await _loop_reply(app, conn, "test", send)
        token_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "token"]
        assert len(token_msgs) >= 2

    @pytest.mark.asyncio
    async def test_reply_error_sends_error(self):
        def failing_reply(msg, sess):
            raise ValueError("boom")

        app = MagicMock()
        app._reply_fn = failing_reply
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        await _loop_reply(app, conn, "test", send)
        error_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "error"]
        assert len(error_msgs) >= 1

    @pytest.mark.asyncio
    async def test_stop_cancels_gen_reply(self):
        async def gen_reply(msg, sess):
            yield "chunk1"
            await asyncio.sleep(5)
            yield "chunk2"

        app = MagicMock()
        app._reply_fn = gen_reply
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        await _loop_reply(app, conn, "test", send)
        # Without stop, both chunks should be sent
        token_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "token"]
        assert len(token_msgs) >= 2

    @pytest.mark.asyncio
    async def test_stop_during_gen_reply(self):
        """Stop mid-generation should break after current chunk."""
        chunks_sent = []

        async def gen_reply(msg, sess):
            chunks_sent.append("chunk1")
            yield "chunk1"
            await asyncio.sleep(0.05)
            chunks_sent.append("chunk2")
            yield "chunk2"
            chunks_sent.append("chunk3")
            yield "chunk3"

        app = MagicMock()
        app._reply_fn = gen_reply
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()

        # Stop after first chunk yields
        async def delayed_stop():
            await asyncio.sleep(0.01)
            conn.request_stop()

        await asyncio.gather(
            _loop_reply(app, conn, "test", send),
            delayed_stop(),
        )
        token_msgs = [c for c in send.call_args_list if c[0][0].get("type") == "token"]
        assert len(token_msgs) >= 1


class TestHandleWidgetEvent:
    def test_no_handlers(self):
        app = MagicMock()
        app._on_handlers = {}
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        asyncio.run(_handle_widget_event(app, {"event": "unknown", "key": "k"}, send, conn))
        # Should not error, just log debug

    def test_handler_fires(self):
        app = MagicMock()
        results = []

        def handler(data):
            results.append(data)
            return "ok"
        app._on_handlers = {"button_click": [handler]}
        app._emit_handler_result = AsyncMock()
        conn = ConnectionState(system_prompt="")
        send = AsyncMock()
        asyncio.run(_handle_widget_event(app, {"event": "button_click", "key": "submit", "data": {"key": "submit"}}, send, conn))
        assert len(results) == 1


class TestWebSocketAuth:
    def test_ws_auth_rejected(self):
        app = ChatUI(provider="echo", open_browser=False, port=8775,
                     reply=lambda m, s: "ok", auth_key="secret123")
        from starlette.websockets import WebSocketDisconnect
        with TestClient(app.app) as client:
            try:
                with client.websocket_connect("/ws?token=wrong"):
                    pass
            except WebSocketDisconnect as e:
                assert e.code == 4001

    def test_ws_auth_accepted(self):
        app = ChatUI(provider="echo", open_browser=False, port=8776,
                     reply=lambda m, s: "ok", auth_key="secret123")
        with TestClient(app.app) as client:
            with client.websocket_connect("/ws?token=secret123") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "config"


class TestNoKeyMessage:
    def test_no_key_msg_render(self):
        from chatui._constants import _no_key_msg, _ENV_KEYS
        msg = _no_key_msg("groq")
        assert "GROQ_API_KEY" in msg
        msg2 = _no_key_msg("ollama")
        assert "Ollama" in msg2

    def test_check_api_key_success(self, monkeypatch):
        from chatui._constants import _check_api_key
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        assert _check_api_key("groq", None) == "test-key"

    def test_check_api_key_no_env(self, monkeypatch):
        from chatui._constants import _check_api_key
        from chatui.exceptions import ChatUIMissingKeyError
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(ChatUIMissingKeyError):
            _check_api_key("groq", None)

    def test_check_api_key_ollama(self):
        from chatui._constants import _check_api_key
        assert _check_api_key("ollama", None) == "ollama"


class TestBuilderEdgeCases:
    def test_health_dev_mode(self):
        app = ChatUI(provider="echo", open_browser=False, port=8777,
                     reply=lambda m, s: "ok")
        from fastapi.testclient import TestClient
        with TestClient(app.app) as client:
            r = client.get("/health")
            assert r.status_code == 200
            body = r.json()
            assert "version" in body
            assert body["status"] == "ok"

    def test_health_prod_mode(self):
        import os
        os.environ["CHATUI_ENV"] = "production"
        try:
            app = ChatUI(provider="echo", open_browser=False, port=8778,
                         reply=lambda m, s: "ok")
            from fastapi.testclient import TestClient
            with TestClient(app.app) as client:
                r = client.get("/health")
                assert r.status_code == 200
                body = r.json()
                assert body == {"status": "ok"}
        finally:
            os.environ.pop("CHATUI_ENV", None)

    def test_root_serves_html(self):
        app = ChatUI(provider="echo", open_browser=False, port=8779,
                     reply=lambda m, s: "ok", title="TestTitle",
                     subtitle="TestSub", chips=["Hello", "World"])
        from fastapi.testclient import TestClient
        with TestClient(app.app) as client:
            r = client.get("/")
            assert r.status_code == 200
            html = r.text
            assert "TestTitle" in html
            assert "TestSub" in html
            assert "Hello" in html
            assert "World" in html
