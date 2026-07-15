"""
chatui/api.py
Beginner-facing API — the simplest way to start a chatbot.

    from chatui import chat
    chat()

    # With tools
    def get_weather(city: str) -> dict:
        '''Current weather for a city.'''
        return {"city": city, "temp": "22C"}

    chat(tools=[get_weather], title="Weather Bot")
"""
from __future__ import annotations

from typing import Any, Callable

from .app import ChatUI
from ._constants import VERSION


def chat(
    *,
    tools: list[Callable] | None = None,
    components: dict[str, Callable] | None = None,
    on: dict[str, Callable] | None = None,
    reply: Callable | None = None,
    title: str = "ChatUI",
    theme: str = "manuscript",
    provider: str = "auto",
    model: str | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    **kwargs: Any,
) -> None:
    """
    Start a ChatUI server with minimal ceremony.

    Auto-detects provider from environment variables when provider="auto".
    Supports plain-function registration (no decorators required).

    Args:
        tools: List of plain functions to register as tools.
        components: Dict of {name: renderer_fn} for HTML components.
        on: Dict of {event: handler} for widget events.
        reply: Custom reply function (sync, async, or async generator).
            When provided, no LLM provider is needed.
        title: Browser tab and sidebar title.
        theme: Theme name.
        provider: "auto" (default) or explicit provider name.
        model: Override the default model for the provider.
        host: Bind address.
        port: Bind port.
        **kwargs: Pass through to ChatUI.
    """
    app = ChatUI(
        provider=provider,
        model=model,
        title=title,
        theme=theme,
        host=host,
        port=port,
        tools=tools,
        components=components,
        on=on,
        reply=reply,
        **kwargs,
    )
    app.run()


__all__ = ["chat", "ChatUI", "VERSION"]
