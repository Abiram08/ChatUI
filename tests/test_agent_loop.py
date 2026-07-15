"""Mocked LLM stream tests for the unified agent loop and provider adapters."""
from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from chatui.providers.base import (
    EndEvent, ErrorEvent, TokenEvent, ToolCallEvent,
)
from chatui.runtime.connection import ConnectionState
from chatui.tools import ToolRegistry
from chatui.widgets import button, metric


class MockProvider:
    """Mock provider that yields predetermined events across multiple rounds."""

    def __init__(self, rounds):
        """Args: list of event lists, one per round."""
        self._rounds = list(rounds)
        self._round_idx = 0
        self._provider_name = "mock"
        self._model = "mock-model"

    async def stream(self, messages, tools, system, stop_event):
        if self._round_idx >= len(self._rounds):
            yield EndEvent(stop_reason="end_turn")
            return
        events = self._rounds[self._round_idx]
        self._round_idx += 1
        for event in events:
            if stop_event.is_set():
                break
            yield event

    def append_assistant(self, history, text, tool_calls):
        content = []
        if text:
            content.append({"type": "text", "text": text})
        for tc in tool_calls:
            content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
        history.append({"role": "assistant", "content": content})

    def append_tool_result(self, history, *args):
        if len(args) == 2 and isinstance(args[0], str):
            history.append({"role": "tool", "tool_call_id": args[0], "content": args[1]})
        elif len(args) == 1 and isinstance(args[0], list):
            history.append({"role": "user", "content": args[0]})


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_simple_text_response(self):
        from chatui.agent.loop import agent_loop

        provider = MockProvider([[
            TokenEvent(text="Hello "),
            TokenEvent(text="world!"),
            EndEvent(stop_reason="end_turn", input_tokens=10, output_tokens=5),
        ]])
        conn = ConnectionState(system_prompt="test")
        sent = []

        async def send(payload):
            sent.append(payload)

        registry = ToolRegistry()

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=registry, components=None,
        )

        assert any(p["type"] == "start" or p["type"] == "token" for p in sent)
        assert any(p["type"] == "token" and "Hello" in p.get("content", "") for p in sent)
        assert sent[-1]["type"] == "end"
        assert sent[-1]["usage"]["input"] == 10
        assert sent[-1]["usage"]["output"] == 5

    @pytest.mark.asyncio
    async def test_tool_call_flow(self):
        from chatui.agent.loop import agent_loop

        provider = MockProvider([
            [  # Round 1: tool call
                TokenEvent(text="Let me check..."),
                ToolCallEvent(id="tc1", name="get_weather", input={"city": "Tokyo"}),
                EndEvent(stop_reason="tool_use", input_tokens=15, output_tokens=10),
            ],
            [  # Round 2: final response
                TokenEvent(text="The weather in Tokyo is sunny."),
                EndEvent(stop_reason="end_turn", input_tokens=25, output_tokens=15),
            ],
        ])
        conn = ConnectionState(system_prompt="test")
        sent = []

        async def send(payload):
            sent.append(payload)

        registry = ToolRegistry()

        def get_weather(city: str) -> dict:
            """Get weather."""
            return {"city": city, "temp": "22C"}
        registry.register(get_weather)

        async def run_tool(name, inputs):
            return await asyncio.to_thread(registry.execute, name, inputs)

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=registry, components=None,
            run_tool=run_tool,
        )

        # Should have tool_call and tool_result messages
        tool_calls = [p for p in sent if p["type"] == "tool_call"]
        tool_results = [p for p in sent if p["type"] == "tool_result"]
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "get_weather"
        assert len(tool_results) == 1
        assert "22C" in tool_results[0]["result"]
        # Should have start_again after tool execution
        assert any(p["type"] == "start_again" for p in sent)
        # Should end with end
        assert sent[-1]["type"] == "end"

    @pytest.mark.asyncio
    async def test_stop_cancels_generation(self):
        from chatui.agent.loop import agent_loop

        provider = MockProvider([[
            TokenEvent(text="Hello"),
            EndEvent(stop_reason="end_turn"),
        ]])
        conn = ConnectionState(system_prompt="test")
        conn.request_stop()  # Pre-stopped
        sent = []

        async def send(payload):
            sent.append(payload)

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=ToolRegistry(), components=None,
        )

        assert sent[0]["type"] == "stopped"

    @pytest.mark.asyncio
    async def test_error_event(self):
        from chatui.agent.loop import agent_loop

        provider = MockProvider([[
            ErrorEvent(message="API rate limit exceeded"),
        ]])
        conn = ConnectionState(system_prompt="test")
        sent = []

        async def send(payload):
            sent.append(payload)

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=ToolRegistry(), components=None,
        )

        assert sent[-1]["type"] == "error"
        assert "rate limit" in sent[-1]["content"]

    @pytest.mark.asyncio
    async def test_widget_side_effects_from_tool(self):
        from chatui.agent.loop import agent_loop

        provider = MockProvider([
            [  # Round 1: tool call
                ToolCallEvent(id="tc1", name="show_widgets", input={}),
                EndEvent(stop_reason="tool_use"),
            ],
            [  # Round 2: end
                EndEvent(stop_reason="end_turn"),
            ],
        ])
        conn = ConnectionState(system_prompt="test")
        sent = []

        async def send(payload):
            sent.append(payload)

        registry = ToolRegistry()

        def show_widgets() -> tuple:
            """Show widgets."""
            return (metric("Revenue", "$1M", delta="+12%"), button("OK", key="ok"))
        registry.register(show_widgets)

        async def run_tool(name, inputs):
            return await asyncio.to_thread(registry.execute, name, inputs)

        await agent_loop(
            provider=provider, conn=conn, send=send,
            registry=registry, components=None,
            run_tool=run_tool,
        )

        widget_msgs = [p for p in sent if p["type"] == "widgets"]
        assert len(widget_msgs) >= 1
        assert any(w["widget"] == "metric" for w in widget_msgs[0]["widgets"])


class TestAnthropicProvider:
    def test_initialization(self):
        from chatui.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        provider = AnthropicProvider(client=mock_client, model="claude-3")
        assert provider._client is mock_client
        assert provider._model == "claude-3"

    def test_append_assistant_with_text(self):
        from chatui.providers.anthropic import AnthropicProvider
        from chatui.providers.base import ToolCallEvent

        provider = AnthropicProvider(client=MagicMock(), model="claude-3")
        history = []
        provider.append_assistant(history, "Hello", [])
        assert len(history) == 1
        assert history[0]["role"] == "assistant"
        assert history[0]["content"][0]["text"] == "Hello"

    def test_append_assistant_with_tool_use(self):
        from chatui.providers.anthropic import AnthropicProvider
        from chatui.providers.base import ToolCallEvent

        provider = AnthropicProvider(client=MagicMock(), model="claude-3")
        history = []
        tc = ToolCallEvent(id="tc1", name="search", input={"q": "test"})
        provider.append_assistant(history, "Searching...", [tc])
        assert len(history) == 1
        content = history[0]["content"]
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"
        assert content[1]["id"] == "tc1"

    def test_append_tool_result(self):
        from chatui.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(client=MagicMock(), model="claude-3")
        history = []
        tool_results = [
            {"type": "tool_result", "tool_use_id": "tc1", "content": "result data"},
        ]
        provider.append_tool_result(history, tool_results)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == tool_results


class TestOpenAICompatProvider:
    def test_initialization(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        mock_client = MagicMock()
        provider = OpenAICompatProvider(client=mock_client, model="gpt-4", provider_name="groq")
        assert provider._client is mock_client
        assert provider._model == "gpt-4"
        assert provider._provider_name == "groq"

    def test_append_assistant_with_tool_calls(self):
        from chatui.providers.openai_compat import OpenAICompatProvider
        from chatui.providers.base import ToolCallEvent

        provider = OpenAICompatProvider(client=MagicMock(), model="gpt-4", provider_name="openai")
        history = []
        tc = ToolCallEvent(id="call_1", name="search", input={"q": "test"})
        provider.append_assistant(history, "Searching", [tc])
        assert len(history) == 1
        assert history[0]["role"] == "assistant"
        assert history[0]["tool_calls"][0]["id"] == "call_1"
        assert history[0]["tool_calls"][0]["function"]["name"] == "search"

    def test_append_tool_result(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider(client=MagicMock(), model="gpt-4", provider_name="openai")
        history = []
        provider.append_tool_result(history, "call_1", "result data")
        assert len(history) == 1
        assert history[0]["role"] == "tool"
        assert history[0]["tool_call_id"] == "call_1"
        assert history[0]["content"] == "result data"


class TestProviderDetection:
    def test_detect_groq(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test")
        from chatui.providers.detect import detect_provider_from_env
        provider, model = detect_provider_from_env()
        assert provider == "groq"

    def test_detect_openai(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        from chatui.providers.detect import detect_provider_from_env
        provider, model = detect_provider_from_env()
        assert provider == "openai"

    def test_detect_anthropic(self, monkeypatch):
        for k in ("GROQ_API_KEY", "OPENAI_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        from chatui.providers.detect import detect_provider_from_env
        provider, model = detect_provider_from_env()
        assert provider == "anthropic"

    def test_no_provider_raises(self, monkeypatch):
        for k in ("GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        from chatui.exceptions import ChatUINoProviderError
        from chatui.providers.detect import detect_provider_from_env
        with pytest.raises(ChatUINoProviderError):
            detect_provider_from_env()
