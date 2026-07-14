"""
ChatUI — Minimal starter
Three lines to a production chatbot.
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

if __name__ == "__main__":
    app.run()
