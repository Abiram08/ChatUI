import os
from chatui import ChatUI

ChatUI(
    provider = "groq",
    api_key  = os.getenv("GROQ_API_KEY"),
    title    = "My Assistant",
    logo     = "✦",
).run()
