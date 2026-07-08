"""
chatui/session.py
Per-connection session state — like st.session_state but for chatbots.
Survives across conversation turns within the same WebSocket connection.
"""
import json
import uuid
from typing import Any


class SessionState:
    """
    A dict-like namespace that persists across conversation turns.

    Usage:
        from chatui import ChatUI

        app = ChatUI(...)

        @app.tool
        def remember(key: str, value: str):
            app.session[key] = value
            return {"stored": key}

        @app.context
        def inject_session():
            return dict(app.session)
    """

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._session_id: str = uuid.uuid4().hex[:12]

    @property
    def id(self) -> str:
        return self._session_id

    def reset(self) -> None:
        self._data.clear()
        self._session_id = uuid.uuid4().hex[:12]

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self) -> str:
        return f"SessionState({json.dumps(self._data, default=str, indent=2)})"

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
