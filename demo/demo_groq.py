"""
ChatUI v1.0 — Minimal Starter
The fastest way to get a production chatbot running.
"""
import os
from chatui import ChatUI

app = ChatUI(
    provider="groq",
    api_key=os.getenv("GROQ_API_KEY"),
    title="My Chatbot",
    logo="+",
    subtitle="Ask me anything.",
    theme="manuscript",
    chips=["Hello!", "Tell me a joke", "What can you do?"],
)

app.run()
