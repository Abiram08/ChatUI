"""
Async demo — uses an async reply function.
Run: python demo/demo_async.py
"""
import asyncio
from chatui import chat


async def async_echo(message, session):
    """Async function that simulates work."""
    await asyncio.sleep(0.3)
    return f"Async reply: {message}"


chat(
    reply=async_echo,
    title="Async Demo",
    subtitle="Uses an async reply function",
    theme="light",
)
