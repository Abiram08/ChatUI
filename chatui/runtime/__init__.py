"""
chatui/runtime/__init__.py
Runtime state management for ChatUI connections.
"""
from .connection import ConnectionState
from .history import truncate_history, repair_tool_pairs

__all__ = ["ConnectionState", "truncate_history", "repair_tool_pairs"]
