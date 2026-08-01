"""Echo demo — no API key needed.

Run: python demo/demo_echo.py
Then open http://localhost:8000
"""
from chatui import chat


def echo(message, session):
    return f"You said: {message}"


chat(
    reply=echo,
    title="Echo Bot",
    subtitle="No API key needed — just type something",
    chips=["Hello!", "What can you do?", "Tell me a joke"],
)
