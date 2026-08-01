"""
Tabs layout demo — uses the tabs layout instead of sidebar.
Run: python demo/demo_tabs.py
"""
from chatui import chat


def echo(message, session):
    return f"You said: {message}"


chat(
    reply=echo,
    title="Tabs Demo",
    subtitle="Using the tabs layout — sidebar opens as drawer",
    layout="tabs",
    theme="slate",
    chips=["Hello", "How does tabs work?", "Show me"],
)
