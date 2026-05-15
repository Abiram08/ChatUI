"""
chatui — The Python chatbot framework that doesn't suck.

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

__all__    = ["ChatUI"]
__version__ = "0.2.0"


def main():
    """Entry point for `chatui` CLI."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY not set.")
        return
    ChatUI(api_key=key).run()
