"""
chatui/providers/anthropic.py
Anthropic provider adapter.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from .base import EndEvent, ErrorEvent, TokenEvent, ToolCallEvent

logger = logging.getLogger("chatui")


class AnthropicProvider:
    """Anthropic adapter — translates Anthropic stream into Events."""

    def __init__(self, client: Any, model: str):
        self._client = client
        self._model = model

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        system: str,
        stop_event: Any,
    ) -> AsyncIterator:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        full_text = ""
        stop_reason = "end_turn"
        total_in = total_out = 0
        tool_uses = []

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if stop_event.is_set():
                        break
                    if (
                        getattr(event, "type", None) == "content_block_delta"
                        and hasattr(event, "delta")
                        and getattr(event.delta, "text", None)
                    ):
                        chunk = event.delta.text
                        full_text += chunk
                        yield TokenEvent(text=chunk)

                final = await stream.get_final_message()
                stop_reason = final.stop_reason
                total_in = final.usage.input_tokens
                total_out = final.usage.output_tokens
                for block in final.content:
                    if block.type == "tool_use":
                        tool_uses.append(block)
        except Exception as e:
            logger.exception("Anthropic stream error")
            yield ErrorEvent(message=str(e))
            return

        for tu in tool_uses:
            yield ToolCallEvent(id=tu.id, name=tu.name, input=tu.input)

        yield EndEvent(
            stop_reason=stop_reason,
            input_tokens=total_in,
            output_tokens=total_out,
        )

    @staticmethod
    def format_history_for_provider(history: list[dict]) -> list[dict]:
        """Convert internal history to Anthropic format (already compatible)."""
        return history

    @staticmethod
    def append_assistant(history: list[dict], text: str, tool_uses: list) -> None:
        """Append an assistant message with text and tool_use blocks."""
        content = []
        if text:
            content.append({"type": "text", "text": text})
        for tu in tool_uses:
            content.append({
                "type": "tool_use",
                "id": tu.id,
                "name": tu.name,
                "input": tu.input,
            })
        history.append({"role": "assistant", "content": content})

    @staticmethod
    def append_tool_result(history: list[dict], tool_results: list[dict]) -> None:
        """Append tool results as a user message."""
        history.append({"role": "user", "content": tool_results})
