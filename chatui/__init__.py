"""
chatui - The fastest way to ship a production AI chatbot.

    # One-liner (auto-detects provider from environment)
    from chatui import chat
    chat()

    # With tools (plain functions, no decorators)
    def get_weather(city: str) -> dict:
        '''Current weather for a city.'''
        return {"city": city, "temp": "22C"}

    chat(tools=[get_weather], title="Weather Bot")

    # Custom reply (no LLM key needed)
    def echo(message: str, session) -> str:
        return f"You said: {message}"

    chat(reply=echo, title="Echo Bot")

Advanced (decorators)::

    app = ChatUI(provider="groq")

    @app.tool
    def get_weather(city: str) -> dict:
        '''Current weather for a city.'''
        return {"city": city, "temp": "22C"}

    @app.component("chart")
    def chart(data: dict) -> str:
        return f"<b>{data.get('title', 'Chart')}</b>"

    app.run()
"""
from .app import ChatUI
from ._constants import VERSION
from .session import SessionState
from .api import chat
from .widgets import (
    Widget,
    button,
    checkbox,
    choice,
    columns,
    confirm,
    divider,
    end_columns,
    end_expander,
    expander,
    file_uploader,
    form,
    html,
    image,
    markdown,
    metric,
    progress,
    radio,
    selectbox,
    slider,
    spinner,
    stack,
    status,
    table,
    text_input,
    toast,
    actions,
    row,
    card,
)

__all__ = [
    "ChatUI",
    "SessionState",
    "VERSION",
    "Widget",
    "chat",
    "button",
    "text_input",
    "selectbox",
    "radio",
    "checkbox",
    "slider",
    "progress",
    "status",
    "table",
    "markdown",
    "html",
    "image",
    "divider",
    "metric",
    "columns",
    "end_columns",
    "expander",
    "end_expander",
    "toast",
    "file_uploader",
    "spinner",
    "actions",
    "row",
    "stack",
    "card",
    "choice",
    "form",
    "confirm",
]

__version__ = VERSION


def chat(
    *,
    tools=None,
    components=None,
    on=None,
    reply=None,
    title="ChatUI",
    theme="manuscript",
    provider="auto",
    model=None,
    host="0.0.0.0",
    port=8000,
    **kwargs,
):
    """Start a ChatUI server with minimal ceremony.

    Auto-detects provider from environment variables when provider="auto".
    """
    from .api import chat as _chat

    return _chat(
        tools=tools,
        components=components,
        on=on,
        reply=reply,
        title=title,
        theme=theme,
        provider=provider,
        model=model,
        host=host,
        port=port,
        **kwargs,
    )


def main():
    """Entry point for the ``chatui`` CLI."""
    import argparse
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="chatui",
        description="ChatUI - production-ready AI chatbot interface",
    )
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "anthropic", "ollama", "groq", "openai"],
    )
    parser.add_argument("--model", default=None, help="Override the default model")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--theme", default="manuscript")
    parser.add_argument("--title", default="ChatUI")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
    )
    parser.add_argument("--auth-key", default=None, help="Bearer / ?token= secret")
    parser.add_argument("--rate-limit", type=int, default=0, help="Requests per minute (0=off)")
    parser.add_argument("--no-browser", action="store_true", default=False)
    parser.add_argument("--version", action="version", version=f"chatui {__version__}")
    args = parser.parse_args()

    # Auto-detect provider
    if args.provider == "auto":
        try:
            from .providers.detect import detect_provider_from_env

            provider, default_model = detect_provider_from_env()
            if args.model is None:
                args.model = default_model
        except Exception as e:
            print(str(e))
            sys.exit(1)
    else:
        provider = args.provider

    app = ChatUI(
        provider=provider,
        model=args.model,
        host=args.host,
        port=args.port,
        theme=args.theme,
        title=args.title,
        open_browser=not args.no_browser,
        log_level=args.log_level,
        auth_key=args.auth_key,
        rate_limit=args.rate_limit,
    )
    app.run()
