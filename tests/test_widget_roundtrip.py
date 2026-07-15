"""Widget event round-trip tests: send widget_event, verify handler fires."""
from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient
from chatui import ChatUI, button, metric, actions


def _make_app(reply_fn=None, on_handlers=None):
    app = ChatUI(provider="auto", open_browser=False, port=8780,
                 reply=reply_fn or (lambda msg, sess: "ok"))
    if on_handlers:
        for event, handler in on_handlers.items():
            app.register_handler(event, handler)
    return app


def _drain_bootstrap(ws):
    for _ in range(5):
        msg = ws.receive_json()
        if msg.get("type") == "session_state":
            break


def _recv_until(ws, stop_types, max_msgs=10):
    """Receive messages until we hit a stop type or max."""
    events = []
    for _ in range(max_msgs):
        msg = ws.receive_json()
        events.append(msg)
        if msg.get("type") in stop_types:
            break
    return events


class TestWidgetEventRoundTrip:
    def test_button_click_triggers_handler(self):
        clicked = []
        def handler(data):
            clicked.append(data.get("key"))
            return f"Clicked {data.get('key')}"
        app = _make_app(on_handlers={"button_click": handler})
        with TestClient(app.app).websocket_connect("/ws") as ws:
            _drain_bootstrap(ws)
            ws.send_json({"action": "widget_event", "event": "button_click", "key": "submit", "value": True, "data": {"key": "submit"}})
            events = _recv_until(ws, {"end"})
            assert clicked == ["submit"]

    def test_handler_by_widget_key(self):
        results = []
        def handler(data):
            results.append(data.get("key"))
            return "Done!"
        app = _make_app(on_handlers={"refresh": handler})
        with TestClient(app.app).websocket_connect("/ws") as ws:
            _drain_bootstrap(ws)
            ws.send_json({"action": "widget_event", "event": "button_click", "key": "refresh", "data": {"key": "refresh"}})
            events = _recv_until(ws, {"end"})
            assert results == ["refresh"]

    def test_handler_returns_widgets(self):
        def handler(data):
            return metric("Status", "Online", delta="+5%")
        app = _make_app(on_handlers={"button_click": handler})
        with TestClient(app.app).websocket_connect("/ws") as ws:
            _drain_bootstrap(ws)
            ws.send_json({"action": "widget_event", "event": "button_click", "key": "show", "data": {"key": "show"}})
            # Pure widgets returns without 'end' — stop on 'widgets'
            events = _recv_until(ws, {"widgets"})
            widget_msgs = [e for e in events if e["type"] == "widgets"]
            assert len(widget_msgs) >= 1

    def test_handler_error_sends_error(self):
        def handler(data):
            raise ValueError("Handler crashed")
        app = _make_app(on_handlers={"button_click": handler})
        with TestClient(app.app).websocket_connect("/ws") as ws:
            _drain_bootstrap(ws)
            ws.send_json({"action": "widget_event", "event": "button_click", "key": "crash", "data": {"key": "crash"}})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Handler error" in msg["content"]

    def test_async_handler_works(self):
        results = []
        async def handler(data):
            results.append(data.get("key"))
            return "Async result"
        app = _make_app(on_handlers={"button_click": handler})
        with TestClient(app.app).websocket_connect("/ws") as ws:
            _drain_bootstrap(ws)
            ws.send_json({"action": "widget_event", "event": "button_click", "key": "async", "data": {"key": "async"}})
            events = _recv_until(ws, {"end"})
            assert results == ["async"]
            token_content = "".join(e.get("content", "") for e in events if e["type"] == "token")
            assert "Async result" in token_content
