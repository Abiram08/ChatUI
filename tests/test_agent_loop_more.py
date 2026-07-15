"""Additional agent loop tests: component detection, max tool rounds, error paths."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from chatui.providers.base import EndEvent, ErrorEvent, TokenEvent, ToolCallEvent
from chatui.runtime.connection import ConnectionState
from chatui.tools import ComponentRegistry
from chatui.agent.loop import _check_component, _emit_tool_side_effects


class TestCheckComponent:
    def test_exact_json_component(self):
        components = ComponentRegistry()
        components.register("chart", lambda d: f"<div>{d.get('label', '')}</div>")

        text = '{"component": "chart", "data": {"label": "Sales"}}'
        result = _check_component(text, components)
        assert result is not None
        name, html = result
        assert name == "chart"
        assert "Sales" in html

    def test_fenced_json_component(self):
        components = ComponentRegistry()
        components.register("badge", lambda d: f"<span>{d.get('text', '')}</span>")

        text = '```json\n{"component": "badge", "data": {"text": "Hello"}}\n```'
        result = _check_component(text, components)
        assert result is not None
        assert result[0] == "badge"

    def test_prose_json_component(self):
        components = ComponentRegistry()
        components.register("card", lambda d: f"<b>{d.get('title', '')}</b>")

        text = 'Here is the data: {"component": "card", "data": "simple"}'
        result = _check_component(text, components)
        assert result is not None
        assert result[0] == "card"

    def test_no_component_returns_none(self):
        components = ComponentRegistry()
        components.register("chart", lambda d: "<div></div>")

        text = "Just some regular text"
        result = _check_component(text, components)
        assert result is None

    def test_unknown_component_returns_none(self):
        components = ComponentRegistry()
        text = '{"component": "unknown", "data": {}}'
        result = _check_component(text, components)
        assert result is None

    def test_invalid_json_returns_none(self):
        components = ComponentRegistry()
        text = '{"component": "chart", "data": }'
        result = _check_component(text, components)
        assert result is None

    def test_no_components_registered(self):
        components = ComponentRegistry()
        text = '{"component": "chart", "data": {}}'
        result = _check_component(text, components)
        assert result is None

    def test_component_in_code_fence_no_lang(self):
        components = ComponentRegistry()
        components.register("chart", lambda d: f"<div>{d.get('label', '')}</div>")

        text = '```\n{"component": "chart", "data": {"label": "Revenue"}}\n```'
        result = _check_component(text, components)
        assert result is not None
        assert result[0] == "chart"

    def test_prose_with_component_keyword_but_no_valid_json(self):
        components = ComponentRegistry()
        components.register("chart", lambda d: "<div></div>")

        text = 'The component is called "chart" but it is not JSON.'
        result = _check_component(text, components)
        assert result is None


class TestEmitToolSideEffects:
    @pytest.mark.asyncio
    async def test_no_widgets(self):
        send = MagicMock()
        result = {"ok": True, "value": 42}
        registry = MagicMock()
        registry.to_json.return_value = '{"ok": true, "value": 42}'
        text = await _emit_tool_side_effects(send, result, registry)
        send.assert_not_called()
        assert text == '{"ok": true, "value": 42}'

    @pytest.mark.asyncio
    async def test_with_widgets(self):
        from chatui import metric

        send = AsyncMock()
        result = (metric("Revenue", "$1M"), {"ok": True})
        registry = MagicMock()
        registry.to_json.return_value = '{"ok": true}'
        text = await _emit_tool_side_effects(send, result, registry)
        send.assert_called_once()
        assert send.call_args[0][0]["type"] == "widgets"
        assert text == '{"ok": true}'


class TestAgentLoopMaxRounds:
    @pytest.mark.asyncio
    async def test_max_tool_rounds_stops(self):
        from chatui.agent.loop import agent_loop

        class EndlessProvider:
            _provider_name = "mock"
            _model = "mock"

            async def stream(self, messages, tools, system, stop_event):
                yield TokenEvent(text="thinking...")
                yield ToolCallEvent(id="tc1", name="ping", input={})
                yield EndEvent(stop_reason="tool_use")

            def append_assistant(self, history, text, tool_calls):
                history.append({"role": "assistant", "content": text or ""})

            def append_tool_result(self, history, *args):
                if len(args) == 2:
                    history.append({"role": "tool", "tool_call_id": args[0], "content": args[1]})

        provider = EndlessProvider()
        conn = ConnectionState(system_prompt="test")
        sent = []

        async def send(payload):
            sent.append(payload)

        # Simple ping tool
        def ping() -> str:
            return "pong"

        from chatui.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register(ping)

        async def run_tool(name, inputs):
            return "pong"

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=reg, components=None,
            run_tool=run_tool,
        )

        # Should have an error about max tool rounds
        error_msgs = [p for p in sent if p["type"] == "error"]
        assert len(error_msgs) >= 1
        assert "tool rounds" in error_msgs[-1]["content"]
