"""Mocked stream tests for AnthropicProvider and OpenAICompatProvider."""
from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from chatui.providers.base import EndEvent, ErrorEvent, TokenEvent, ToolCallEvent


class TestAnthropicProviderStream:
    """Test AnthropicProvider.stream() with mocked Anthropic SDK client."""

    def _make_mock_stream(self, events_config):
        """Create a mock Anthropic stream that yields configured events."""
        chunks = []
        final_content = []
        final_message = MagicMock()
        final_message.content = final_content

        for cfg in events_config:
            if "text" in cfg:
                delta = MagicMock()
                delta.text = cfg["text"]
                event = MagicMock()
                event.type = "content_block_delta"
                event.delta = delta
                chunks.append(event)
            elif "tool_use_id" in cfg:
                block = MagicMock()
                block.type = "tool_use"
                block.id = cfg["tool_use_id"]
                block.name = cfg.get("name", "")
                block.input = cfg.get("input", {})
                final_content.append(block)

        if any("stop_reason" in c for c in events_config):
            cfg = next(c for c in events_config if "stop_reason" in c)
            final_message.stop_reason = cfg.get("stop_reason", "end_turn")
            final_message.usage = MagicMock()
            final_message.usage.input_tokens = cfg.get("input_tokens", 0)
            final_message.usage.output_tokens = cfg.get("output_tokens", 0)
        else:
            final_message.stop_reason = "end_turn"
            final_message.usage = MagicMock()
            final_message.usage.input_tokens = 0
            final_message.usage.output_tokens = 0

        class MockStream:
            def __init__(self):
                self._idx = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._idx < len(chunks):
                    chunk = chunks[self._idx]
                    self._idx += 1
                    return chunk
                raise StopAsyncIteration

            async def get_final_message(self):
                return final_message

        return MockStream()

    @pytest.mark.asyncio
    async def test_stream_text_only(self):
        from chatui.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.stream = MagicMock(
            return_value=self._make_mock_stream([
                {"text": "Hello "},
                {"text": "world!"},
                {"stop_reason": "end_turn", "input_tokens": 10, "output_tokens": 5},
            ])
        )

        provider = AnthropicProvider(client=mock_client, model="claude-3")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        token_events = [e for e in events if isinstance(e, TokenEvent)]
        end_events = [e for e in events if isinstance(e, EndEvent)]
        assert len(token_events) == 2
        assert token_events[0].text == "Hello "
        assert token_events[1].text == "world!"
        assert len(end_events) == 1
        assert end_events[0].stop_reason == "end_turn"
        assert end_events[0].input_tokens == 10
        assert end_events[0].output_tokens == 5

    @pytest.mark.asyncio
    async def test_stream_tool_call(self):
        from chatui.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.stream = MagicMock(
            return_value=self._make_mock_stream([
                {"text": "Let me search..."},
                {"tool_use_id": "tc1", "name": "search", "input": {"q": "test"}},
                {"stop_reason": "tool_use", "input_tokens": 15, "output_tokens": 10},
            ])
        )

        provider = AnthropicProvider(client=mock_client, model="claude-3")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
        assert len(tool_calls) == 1
        assert tool_calls[0].id == "tc1"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].input == {"q": "test"}

    @pytest.mark.asyncio
    async def test_stream_error(self):
        from chatui.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_client.messages = MagicMock()

        class FailingStream:
            async def __aenter__(self):
                raise Exception("API rate limit exceeded")
            async def __aexit__(self, *args): pass

        mock_client.messages.stream = MagicMock(return_value=FailingStream())

        provider = AnthropicProvider(client=mock_client, model="claude-3")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert "rate limit" in error_events[0].message

    @pytest.mark.asyncio
    async def test_stream_stop_cancels(self):
        from chatui.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.stream = MagicMock(
            return_value=self._make_mock_stream([
                {"text": "Hello"},
                {"stop_reason": "end_turn"},
            ])
        )

        provider = AnthropicProvider(client=mock_client, model="claude-3")
        stop_event = asyncio.Event()
        stop_event.set()  # Pre-stopped
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        # Should yield nothing or just an end event since stopped
        token_events = [e for e in events if isinstance(e, TokenEvent)]
        assert len(token_events) == 0

    def test_append_assistant_with_text_and_tools(self):
        from chatui.providers.anthropic import AnthropicProvider
        from chatui.providers.base import ToolCallEvent

        provider = AnthropicProvider(client=MagicMock(), model="claude-3")
        history = []
        tc = ToolCallEvent(id="tc1", name="search", input={"q": "test"})
        provider.append_assistant(history, "Result", [tc])
        assert len(history) == 1
        content = history[0]["content"]
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Result"
        assert content[1]["type"] == "tool_use"
        assert content[1]["id"] == "tc1"

    def test_append_tool_result_batch(self):
        from chatui.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(client=MagicMock(), model="claude-3")
        history = []
        tool_results = [
            {"type": "tool_result", "tool_use_id": "tc1", "content": "data1"},
            {"type": "tool_result", "tool_use_id": "tc2", "content": "data2"},
        ]
        provider.append_tool_result(history, tool_results)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert len(history[0]["content"]) == 2


class TestOpenAICompatProviderStream:
    """Test OpenAICompatProvider.stream() with mocked OpenAI SDK client."""

    def _make_mock_openai_stream(self, chunks_config):
        """Create a mock OpenAI streaming response.

        chunks_config: list of dicts like:
            {"content": "Hello"}
            {"tool_calls": [{"index": 0, "id": "call_1", "name": "search", "arguments": '{"q":"test"}'}]}
            {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        """
        chunks = []
        for cfg in chunks_config:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            delta = MagicMock()
            delta.content = cfg.get("content")
            if "tool_calls" in cfg:
                tc_list = []
                for tc_cfg in cfg["tool_calls"]:
                    tc = MagicMock()
                    tc.index = tc_cfg.get("index", 0)
                    tc.id = tc_cfg.get("id", "")
                    tc.function = MagicMock()
                    tc.function.name = tc_cfg.get("name", "")
                    tc.function.arguments = tc_cfg.get("arguments", "")
                    tc_list.append(tc)
                delta.tool_calls = tc_list
            else:
                delta.tool_calls = None
            chunk.choices[0].delta = delta
            chunk.choices[0].finish_reason = cfg.get("finish_reason")
            chunk.usage = None
            if "usage" in cfg:
                chunk.usage = MagicMock()
                chunk.usage.prompt_tokens = cfg["usage"].get("prompt_tokens", 0)
                chunk.usage.completion_tokens = cfg["usage"].get("completion_tokens", 0)
            chunks.append(chunk)

        class MockStream:
            def __init__(self):
                self._idx = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self._idx < len(chunks):
                    c = chunks[self._idx]
                    self._idx += 1
                    return c
                raise StopAsyncIteration

        return MockStream()

    @pytest.mark.asyncio
    async def test_stream_text_only(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_openai_stream([
                {"content": "Hello "},
                {"content": "world!"},
                {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            ])
        )

        provider = OpenAICompatProvider(client=mock_client, model="gpt-4", provider_name="openai")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        token_events = [e for e in events if isinstance(e, TokenEvent)]
        end_events = [e for e in events if isinstance(e, EndEvent)]
        assert len(token_events) == 2
        assert len(end_events) == 1
        assert end_events[0].stop_reason == "end_turn"
        assert end_events[0].input_tokens == 10
        assert end_events[0].output_tokens == 5

    @pytest.mark.asyncio
    async def test_stream_tool_call(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_openai_stream([
                {"content": "Let me search..."},
                {"tool_calls": [{"index": 0, "id": "call_1", "name": "search", "arguments": '{"q":"test"}'}]},
                {"finish_reason": "tool_calls", "usage": {"prompt_tokens": 15, "completion_tokens": 10}},
            ])
        )

        provider = OpenAICompatProvider(client=mock_client, model="gpt-4", provider_name="openai")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
        assert len(tool_calls) == 1
        assert tool_calls[0].id == "call_1"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].input == {"q": "test"}

        end_events = [e for e in events if isinstance(e, EndEvent)]
        assert end_events[0].stop_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_stream_error(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

        provider = OpenAICompatProvider(client=mock_client, model="gpt-4", provider_name="openai")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert "API error" in error_events[0].message

    @pytest.mark.asyncio
    async def test_stream_ollama_connection_error(self):
        from chatui.providers.openai_compat import OpenAICompatProvider
        from chatui.exceptions import ChatUIOllamaError

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        provider = OpenAICompatProvider(client=mock_client, model="llama3", provider_name="ollama")
        stop_event = asyncio.Event()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert "Ollama" in error_events[0].message or "ollama" in error_events[0].message.lower()

    @pytest.mark.asyncio
    async def test_stream_stop_cancels(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_openai_stream([
                {"content": "Hello"},
                {"finish_reason": "stop"},
            ])
        )

        provider = OpenAICompatProvider(client=mock_client, model="gpt-4", provider_name="openai")
        stop_event = asyncio.Event()
        stop_event.set()
        events = []

        async for event in provider.stream([], None, "system", stop_event):
            events.append(event)

        token_events = [e for e in events if isinstance(e, TokenEvent)]
        assert len(token_events) == 0

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
        args = json.loads(history[0]["tool_calls"][0]["function"]["arguments"])
        assert args == {"q": "test"}

    def test_append_tool_result_individual(self):
        from chatui.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider(client=MagicMock(), model="gpt-4", provider_name="openai")
        history = []
        provider.append_tool_result(history, "call_1", "result data")
        assert len(history) == 1
        assert history[0]["role"] == "tool"
        assert history[0]["tool_call_id"] == "call_1"
        assert history[0]["content"] == "result data"
