"""
chatui/runtime/connection.py
Per-WebSocket connection state.

Fixes the multi-user footgun where one client could change the system
prompt for all connections by mutating shared app-level state.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from ..session import SessionState


@dataclass
class ConnectionState:
    """
    State owned by a single WebSocket connection.

    Each connection gets its own copy of:
    - session (per-user state dict)
    - history (chat messages for this conversation)
    - system_prompt (copy of app default; client updates only this)
    - stop flag (asyncio Event for cancellation)
    - generating flag
    - optional user_id
    """

    session: SessionState = field(default_factory=SessionState)
    history: list = field(default_factory=list)
    system_prompt: str = ""
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    generating: bool = False
    user_id: Optional[str] = None

    @property
    def stop(self) -> bool:
        """True if generation should stop."""
        return self.stop_event.is_set()

    def request_stop(self) -> None:
        """Signal the agent loop to stop."""
        self.stop_event.set()

    def reset_stop(self) -> None:
        """Clear the stop flag for a new generation."""
        self.stop_event.clear()

    def clear_history(self) -> None:
        """Clear chat history."""
        self.history.clear()

    def pop_to_last_user_message(self) -> None:
        """Pop messages until the last user message is at the end (for regenerate)."""
        while self.history:
            last = self.history[-1]
            if last.get("role") == "user" and isinstance(last.get("content"), str):
                break
            self.history.pop()


__all__ = ["ConnectionState"]
