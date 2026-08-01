"""
Full-featured demo — streaming, async, tools simulation.
Run: python demo/demo_full.py
"""
from chatui import chat


def echo_stream(message, session):
    """Stream response word by word (sync generator)."""
    if not message.strip():
        yield "Please say something!"
        return
    words = f"You said: {message}".split()
    for word in words:
        yield word + " "


chat(
    reply=echo_stream,
    title="Streaming Demo",
    subtitle="Sync generator — streams word by word",
    layout="sidebar",
    theme="dark",
    chips=["Hello world", "How are you?", "Tell me a story"],
)
