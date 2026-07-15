"""Echo demo — no LLM key required, uses custom reply callback.

Run: python demo/demo_echo.py
"""
from chatui import chat


def echo(message: str, session) -> str:
    """Echo the user's message back."""
    return f"You said: {message}"


chat(
    reply=echo,
    title="Echo Bot",
    subtitle="No LLM key needed",
)
