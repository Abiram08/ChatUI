"""
chatui/session.py
Per-connection session state — like st.session_state, for chatbots.

Uses contextvars so app.session always points at the active WebSocket
connection while tools / handlers run.
"""
from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from typing import Any, Iterator, Optional


_current_session: ContextVar[Optional["SessionState"]] = ContextVar(
    "chatui_session", default=None
)


def get_current_session() -> Optional["SessionState"]:
    """Return the session bound to the current connection, if any."""
    return _current_session.get()


def set_current_session(session: Optional["SessionState"]):
    """Bind a session to the current async task / thread. Returns a token for reset."""
    return _current_session.set(session)


def reset_current_session(token) -> None:
    """Restore the previous session binding."""
    _current_session.reset(token)


class SessionState:
    """
    Dict-like namespace that persists across turns on one WebSocket connection.

    Usage:
        @app.tool
        def remember(key: str, value: str):
            app.session[key] = value
            return {"stored": key}
    """

    __slots__ = ("_data", "_session_id")

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._session_id: str = uuid.uuid4().hex[:12]

    @property
    def id(self) -> str:
        return self._session_id

    def reset(self) -> None:
        self._data.clear()
        self._session_id = uuid.uuid4().hex[:12]

    # ── dict protocol ─────────────────────────────────────────────────

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        # Always truthy so `session or fallback` patterns work.
        return True

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        try:
            body = json.dumps(self._data, default=str, indent=2)
        except Exception:
            body = str(self._data)
        return f"SessionState(id={self._session_id!r}, data={body})"

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def pop(self, key: str, default: Any = None) -> Any:
        return self._data.pop(key, default)

    def update(self, d: dict) -> None:
        self._data.update(d)

    def clear(self) -> None:
        self._data.clear()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> dict:
        return dict(self._data)
