"""
chatui — The Python chatbot framework that doesn't suck.
The fastest way to ship a production AI chatbot. One import, three lines.

Usage:
    from chatui import ChatUI

    app = ChatUI(api_key="sk-ant-...")

    @app.tool
    def my_function(param: str) -> dict:
        "Description for the AI."
        return {"result": param}

    app.run()
"""
from .server import ChatUI
from .session import SessionState

__all__     = ["ChatUI", "SessionState"]
__version__ = "0.0.1"


def main():
    """Entry point for `chatui` CLI."""
    import argparse, os, sys
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="chatui",
        description="ChatUI — Production-ready AI chatbot interface",
    )
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "ollama", "groq", "openai"])
    parser.add_argument("--model", default=None, help="Override the default model")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--theme", default="manuscript")
    parser.add_argument("--title", default="ChatUI")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    parser.add_argument("--auth-key", default=None, help="Bearer token for auth")
    parser.add_argument("--no-browser", action="store_true", default=False)
    parser.add_argument("--version", action="version", version=f"chatui {__version__}")
    args = parser.parse_args()

    key = os.getenv(_env_key(args.provider))
    if not key and args.provider != "ollama":
        print(f"Error: {_env_key(args.provider)} not set and --api-key not provided.")
        print("Set the environment variable or pass api_key= to ChatUI().")
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
    )
    app.run()


def _env_key(provider: str) -> str:
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": "",
    }
    return mapping.get(provider, "")
