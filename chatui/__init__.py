"""
chatui — The fastest way to ship a production AI chatbot.

    from chatui import ChatUI, button, metric

    app = ChatUI(provider="groq")

    @app.tool
    def hello(name: str) -> dict:
        \"\"\"Greet someone.\"\"\"
        return {"message": f"Hello, {name}!"}

    app.run()
"""
from .server import VERSION, ChatUI
from .session import SessionState
from .widgets import (
    button,
    checkbox,
    columns,
    divider,
    end_columns,
    end_expander,
    expander,
    file_uploader,
    html,
    image,
    markdown,
    metric,
    progress,
    radio,
    selectbox,
    slider,
    spinner,
    status,
    table,
    text_input,
    toast,
    Widget,
)

__all__ = [
    "ChatUI",
    "SessionState",
    "VERSION",
    "Widget",
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
]

__version__ = VERSION


def main():
    """Entry point for the ``chatui`` CLI."""
    import argparse
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="chatui",
        description="ChatUI — production-ready AI chatbot interface",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "ollama", "groq", "openai"],
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

    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": "",
    }
    env_name = env_map.get(args.provider, "")
    key = os.getenv(env_name) if env_name else None

    if not key and args.provider != "ollama":
        print(f"Error: {env_name} is not set.")
        print("Set the environment variable or use ChatUI(api_key=...) in Python.")
        sys.exit(1)

    app = ChatUI(
        provider=args.provider,
        api_key=key,
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
