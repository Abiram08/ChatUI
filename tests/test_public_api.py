"""Smoke tests for the public package surface (Streamlit-like DX)."""
from __future__ import annotations

import chatui
from chatui import (
    ChatUI,
    SessionState,
    VERSION,
    Widget,
    button,
    metric,
    progress,
)


def test_version_exported():
    assert isinstance(VERSION, str)
    assert VERSION
    assert chatui.__version__ == VERSION


def test_widget_builders_exported():
    assert callable(button)
    assert callable(metric)
    assert callable(progress)
    assert issubclass(Widget, object)
    assert issubclass(SessionState, object)


def test_chatui_is_constructible_without_key_for_ollama():
    # Construction should not open network sockets.
    app = ChatUI(provider="ollama", open_browser=False, port=8765)
    assert app.provider == "ollama"
    assert app.theme in ("manuscript",) or isinstance(app.theme, str)
