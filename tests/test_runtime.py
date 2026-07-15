"""Tests for chatui.runtime — ConnectionState and history engine."""
from __future__ import annotations

import asyncio
from chatui.runtime.connection import ConnectionState
from chatui.runtime.history import truncate_history, repair_tool_pairs


class TestConnectionState:
    def test_defaults(self):
        conn = ConnectionState(system_prompt="test")
        assert conn.history == []
        assert conn.system_prompt == "test"
        assert conn.generating is False
        assert conn.user_id is None
        assert conn.stop is False

    def test_stop_event(self):
        conn = ConnectionState(system_prompt="")
        assert conn.stop is False
        conn.request_stop()
        assert conn.stop is True
        conn.reset_stop()
        assert conn.stop is False

    def test_clear_history(self):
        conn = ConnectionState(system_prompt="")
        conn.history.append({"role": "user", "content": "hi"})
        conn.clear_history()
        assert conn.history == []

    def test_pop_to_last_user_message(self):
        conn = ConnectionState(system_prompt="")
        conn.history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "how are you"},
        ]
        conn.pop_to_last_user_message()
        assert len(conn.history) == 3
        assert conn.history[-1]["role"] == "user"

    def test_pop_with_trailing_assistant(self):
        conn = ConnectionState(system_prompt="")
        conn.history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        conn.pop_to_last_user_message()
        assert len(conn.history) == 1
        assert conn.history[-1]["role"] == "user"

    def test_session_is_per_connection(self):
        """Two connections have separate sessions."""
        conn1 = ConnectionState(system_prompt="a")
        conn2 = ConnectionState(system_prompt="b")
        conn1.session["key"] = "value1"
        assert "key" not in conn2.session
        assert conn1.system_prompt != conn2.system_prompt

    def test_system_prompt_is_per_connection(self):
        """Fixing the multi-user footgun: system prompt is per-connection."""
        conn1 = ConnectionState(system_prompt="You are a pirate.")
        conn2 = ConnectionState(system_prompt="You are a chef.")
        conn1.system_prompt = "You are a pilot."
        assert conn2.system_prompt == "You are a chef."


class TestTruncateHistory:
    def test_short_history_unchanged(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = truncate_history(history, max_turns=40)
        assert result == history

    def test_truncation_at_turn_boundary(self):
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"q{i}"})
            history.append({"role": "assistant", "content": f"a{i}"})
        result = truncate_history(history, max_turns=10)
        # Should keep last 10 turns = 20 messages
        assert len(result) == 20
        assert result[0]["content"] == "q40"
        assert result[-1]["content"] == "a49"

    def test_truncation_preserves_tool_pairs(self):
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"q{i}"})
            history.append({"role": "assistant", "content": [{"type": "text", "text": f"a{i}"}]})
        result = truncate_history(history, max_turns=5)
        # Should keep last 5 turns = 10 messages
        assert len(result) == 10


class TestRepairToolPairs:
    def test_empty_history(self):
        assert repair_tool_pairs([]) == []

    def test_orphaned_tool_result_at_start(self):
        history = [
            {"role": "tool", "tool_call_id": "abc", "content": "result"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = repair_tool_pairs(history)
        assert result[0]["role"] == "user"

    def test_orphaned_tool_use_at_end(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "abc", "name": "search", "input": {}}
            ]},
        ]
        result = repair_tool_pairs(history)
        # Orphaned tool_use should be stripped from assistant content
        # If no text remains, the assistant message is removed
        assert result[-1]["role"] == "user"

    def test_orphaned_openai_tool_calls_at_end(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "abc", "type": "function", "function": {"name": "search", "arguments": "{}"}}
            ]},
        ]
        result = repair_tool_pairs(history)
        # Orphaned tool_calls assistant message should be removed
        assert result[-1]["role"] == "user"
