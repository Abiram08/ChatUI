"""
chatui/providers/openai_compat.py
OpenAI-compatible provider adapter (OpenAI, Groq, Ollama, Azure).
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from ..exceptions import ChatUIOllamaError
from .base import EndEvent, ErrorEvent, TokenEvent, ToolCallEvent

logger = logging.getLogger("chatui")


class OpenAICompatProvider:
    """OpenAI-compatible adapter — works with OpenAI, Groq, Ollama, Azure."""

    def __init__(self, client: Any, model: str, provider_name: str = "openai"):
        self._client = client
        self._model = model
        self._provider_name = provider_name

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        system: str,
        stop_event: Any,
    ) -> AsyncIterator:
        full_messages = [{"role": "system", "content": system}] + messages

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": full_messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        full_text = ""
        tc_raw: dict[int, dict] = {}
        finish_reason = "stop"
        total_in = total_out = 0

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if stop_event.is_set():
                    break
                if getattr(chunk, "usage", None):
                    total_in = getattr(chunk.usage, "prompt_tokens", 0) or total_in
                    total_out = getattr(chunk.usage, "completion_tokens", 0) or total_out
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta and delta.content:
                    full_text += delta.content
                    yield TokenEvent(text=delta.content)
                if delta and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tc_raw:
                            tc_raw[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tc_raw[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tc_raw[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tc_raw[idx]["arguments"] += tc.function.arguments
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        except Exception as e:
            msg = str(e)
            if self._provider_name == "ollama" and (
                "connection" in msg.lower() or "connect" in msg.lower()
            ):
                yield ErrorEvent(message=str(ChatUIOllamaError()))
            else:
                logger.exception("OpenAI-compatible stream error")
                yield ErrorEvent(message=msg)
            return

        tool_uses = []
        for idx in sorted(tc_raw):
            raw = tc_raw[idx]
            try:
                input_data = json.loads(raw["arguments"] or "{}")
            except json.JSONDecodeError:
                input_data = {}
            if not isinstance(input_data, dict):
                input_data = {}
            tool_uses.append({
                "id": raw["id"] or f"call_{idx}",
                "name": raw["name"],
                "input": input_data,
            })

        stop_reason = (
            "tool_use"
            if (finish_reason == "tool_calls" and tool_uses)
            else "end_turn"
        )

        for tu in tool_uses:
            yield ToolCallEvent(id=tu["id"], name=tu["name"], input=tu["input"])

        yield EndEvent(
            stop_reason=stop_reason,
            input_tokens=total_in,
            output_tokens=total_out,
        )

    @staticmethod
    def format_history_for_provider(history: list[dict]) -> list[dict]:
        """Convert internal history to OpenAI format (already compatible)."""
        return history

    @staticmethod
    def append_assistant(history: list[dict], text: str, tool_uses: list) -> None:
        """Append an assistant message with text and tool_calls."""
        asst: dict = {"role": "assistant", "content": text or None}
        if tool_uses:
            asst["tool_calls"] = [
                {
                    "id": tu.id if hasattr(tu, "id") else tu["id"],
                    "type": "function",
                    "function": {
                        "name": tu.name if hasattr(tu, "name") else tu["name"],
                        "arguments": json.dumps(tu.input if hasattr(tu, "input") else tu["input"]),
                    },
                }
                for tu in tool_uses
            ]
        history.append(asst)

    @staticmethod
    def append_tool_result(history: list[dict], tool_id: str, result: str) -> None:
        """Append a tool result message."""
        history.append({
            "role": "tool",
            "tool_call_id": tool_id,
            "content": result,
        })
