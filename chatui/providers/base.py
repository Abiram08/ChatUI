"""
chatui/providers/base.py
Provider Protocol and unified event types.

All provider adapters translate their stream chunks into these Events.
The agent loop works with any Provider that implements this Protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable


# ── Event types ─────────────────────────────────────────────────────


@dataclass
class Event:
    """Base agent event."""


@dataclass
class TokenEvent(Event):
    """A text token/chunk from the model."""
    text: str


@dataclass
class ToolCallEvent(Event):
    """Model wants to call a tool."""
    id: str
    name: str
    input: dict


@dataclass
class ToolResultEvent(Event):
    """Tool execution result (sent to model as tool_result)."""
    id: str
    name: str
    result: str


@dataclass
class EndEvent(Event):
    """Generation finished."""
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ErrorEvent(Event):
    """Stream error."""
    message: str


# ── Provider Protocol ──────────────────────────────────────────────


@runtime_checkable
class Provider(Protocol):
    """
    LLM provider interface.

    Adapters translate provider-specific streaming into Events.
    The agent loop calls stream() and handles the Events.
    """

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        system: str,
        stop_event: Any,
    ) -> AsyncIterator[Event]:
        """
        Stream a response from the LLM.

        Args:
            messages: Chat history (provider-specific format).
            tools: Tool schemas (provider-specific format) or None.
            system: System prompt string.
            stop_event: asyncio.Event — set when user clicks Stop.

        Yields:
            Event subclasses (TokenEvent, ToolCallEvent, EndEvent, ErrorEvent).
        """
        ...
