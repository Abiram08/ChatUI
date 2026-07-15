"""Groq demo — minimal starter (1-10 lines mental load).

Requires: GROQ_API_KEY
Set: export GROQ_API_KEY="your-key" (or $env:GROQ_API_KEY on PowerShell)

Run: python demo/demo_groq.py
"""
from chatui import chat

chat(provider="groq", title="Groq Chat")
