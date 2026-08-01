"""
chatui — open-source UI library for AI chatbots.

Write Python, get a streaming chat interface. No frontend build required.

Quickstart::

    from chatui import chat

    def echo(message, session):
        return f"You said: {message}"

    chat(reply=echo, title="Echo Bot")

Features
--------
- Gradio/Streamlit-style Python API
- 2 layouts (sidebar, tabs)
- 4 themes (dark, light, sepia, slate)
- Markdown rendering with code highlighting
- Streaming responses via WebSocket
- Conversation history in localStorage
- Settings panel (theme, font)
"""
from __future__ import annotations

from typing import Any, Callable

from ._server import ChatUI, MessageHandler

VERSION = "0.3.0"


def chat(
    *,
    reply: MessageHandler,
    title: str = "Chat",
    subtitle: str = "",
    logo: str = "\u25c6",
    welcome_title: str = "What can I help with?",
    layout: str = "sidebar",
    theme: str = "dark",
    chips: list[str] | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """Start a ChatUI server with minimal ceremony.

    Parameters
    ----------
    reply : Callable
        Function that handles messages. Receives ``(message, session)``.
        Can be sync, async, sync generator, or async generator.
    title : str, optional
        Page title, by default "Chat"
    subtitle : str, optional
        Subtitle shown below the welcome heading
    logo : str, optional
        Logo character, by default "◆"
    welcome_title : str, optional
        Welcome screen heading, by default "What can I help with?"
    layout : str, optional
        One of "sidebar" or "tabs", by default "sidebar"
    theme : str, optional
        One of "dark", "light", "sepia", "slate", by default "dark"
    chips : list[str] | None, optional
        Suggested prompt chips shown on the welcome screen
    host : str, optional
        Bind address, by default "0.0.0.0"
    port : int, optional
        Bind port, by default 8000

    Examples
    --------
    >>> from chatui import chat
    >>> def echo(message, session):
    ...     return f"You said: {message}"
    >>> chat(reply=echo)
    """
    app = ChatUI(
        reply=reply,
        title=title,
        subtitle=subtitle,
        logo=logo,
        welcome_title=welcome_title,
        layout=layout,
        theme=theme,
        chips=chips,
        host=host,
        port=port,
    )
    app.run()


def main() -> None:
    """CLI entry point. Runs a simple echo server for testing."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="chatui",
        description="ChatUI - open-source chatbot UI library",
    )
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument(
        "--theme",
        default="dark",
        choices=["dark", "light", "sepia", "slate"],
        help="Color theme",
    )
    parser.add_argument(
        "--layout",
        default="sidebar",
        choices=["sidebar", "tabs"],
        help="Layout mode",
    )
    parser.add_argument("--title", default="Chat", help="Page title")
    parser.add_argument(
        "--version",
        action="version",
        version=f"chatui {VERSION}",
    )
    args = parser.parse_args()

    def _echo(message: str, session: dict) -> str:
        return f"Echo: {message}"

    app = ChatUI(
        reply=_echo,
        title=args.title,
        layout=args.layout,
        theme=args.theme,
        host=args.host,
        port=args.port,
    )
    app.run()


__all__ = [
    "chat",
    "ChatUI",
    "MessageHandler",
    "VERSION",
]
