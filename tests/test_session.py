"""Unit tests for chatui.session — SessionState + contextvars."""
from __future__ import annotations

from chatui.session import (
    SessionState,
    get_current_session,
    reset_current_session,
    set_current_session,
)


class TestSessionState:
    def test_id_is_short_hex(self):
        s = SessionState()
        assert isinstance(s.id, str)
        assert len(s.id) == 12

    def test_dict_protocol(self):
        s = SessionState()
        s["user"] = "ada"
        assert s["user"] == "ada"
        assert "user" in s
        assert len(s) == 1
        assert list(s.keys()) == ["user"]
        assert s.get("missing", 42) == 42
        s.set("n", 1)
        assert s.pop("n") == 1
        s.update({"a": 1, "b": 2})
        assert s.to_dict() == {"user": "ada", "a": 1, "b": 2}
        del s["user"]
        assert "user" not in s
        s.clear()
        assert len(s) == 0

    def test_always_truthy(self):
        s = SessionState()
        assert bool(s) is True
        assert (s or "fallback") is s

    def test_reset_clears_and_rotates_id(self):
        s = SessionState()
        old = s.id
        s["x"] = 1
        s.reset()
        assert "x" not in s
        assert s.id != old

    def test_repr_includes_id(self):
        s = SessionState()
        s["k"] = "v"
        r = repr(s)
        assert "SessionState" in r
        assert s.id in r


class TestContextBinding:
    def test_bind_and_reset(self):
        assert get_current_session() is None
        s = SessionState()
        token = set_current_session(s)
        try:
            assert get_current_session() is s
            get_current_session()["bound"] = True
            assert s["bound"] is True
        finally:
            reset_current_session(token)
        assert get_current_session() is None

    def test_nested_rebind(self):
        outer = SessionState()
        inner = SessionState()
        t1 = set_current_session(outer)
        t2 = set_current_session(inner)
        assert get_current_session() is inner
        reset_current_session(t2)
        assert get_current_session() is outer
        reset_current_session(t1)
        assert get_current_session() is None
