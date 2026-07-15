"""
chatui/providers/__init__.py
Provider adapters for LLM streaming.

Each adapter implements the Provider Protocol by translating
provider-specific stream chunks into unified agent Events.
"""
from .base import Provider, Event, TokenEvent, ToolCallEvent, ToolResultEvent, EndEvent, ErrorEvent
from .detect import detect_provider_from_env

__all__ = [
    "Provider",
    "Event",
    "TokenEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "EndEvent",
    "ErrorEvent",
    "detect_provider_from_env",
]
