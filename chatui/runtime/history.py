"""
chatui/runtime/history.py
History truncation and tool-pair repair.

Never truncates mid tool-call pair — Anthropic and OpenAI both require
tool_use/tool_result pairs to stay intact or the API errors.
"""
from __future__ import annotations

from typing import Any


def truncate_history(history: list[dict], max_turns: int = 40) -> list[dict]:
    """
    Truncate chat history at turn boundaries (user -> assistant pairs).

    Never cuts mid tool-call pair. A "turn" is a user message followed by
    its assistant response (which may include tool_use blocks).

    Args:
        history: Full message history list.
        max_turns: Maximum number of user-assistant turn pairs to keep.

    Returns:
        Truncated history list (may be shorter than max_turns * 2
        if tool pairs straddle boundaries).
    """
    if len(history) <= max_turns * 2:
        return list(history)

    # Find turn boundaries: each turn starts at a user message
    turn_starts: list[int] = []
    for i, msg in enumerate(history):
        if msg.get("role") == "user":
            turn_starts.append(i)

    if not turn_starts:
        return list(history)

    # Keep only the last max_turns turns
    kept_starts = turn_starts[-max_turns:]
    start_idx = kept_starts[0]

    # Repair any dangling tool pairs at the cut boundary
    truncated = list(history[start_idx:])
    return repair_tool_pairs(truncated)


def repair_tool_pairs(history: list[dict]) -> list[dict]:
    """
    Ensure tool_use / tool_result pairs are intact.

    If history starts with a tool_result without a preceding assistant
    tool_use, or an assistant with tool_use without following tool_result,
    trim the orphaned messages.

    Args:
        history: Message list (possibly truncated).

    Returns:
        History with intact tool pairs.
    """
    if not history:
        return history

    result = list(history)

    # If first message is a tool result (role=tool) without preceding
    # assistant tool_use, drop it
    while result and result[0].get("role") == "tool":
        result.pop(0)

    # If last message is an assistant with tool_use but no following
    # tool result, we need to check if the tool_use is orphaned
    if result:
        last = result[-1]
        if last.get("role") == "assistant":
            content = last.get("content")
            if isinstance(content, list):
                has_tool_use = any(
                    block.get("type") == "tool_use"
                    for block in content
                    if isinstance(block, dict)
                )
                if has_tool_use:
                    # Check if there are tool results after
                    tool_use_ids = {
                        block.get("id")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "tool_use"
                    }
                    # Look for matching tool_result in next messages
                    # (there shouldn't be any if this is the last message)
                    # Drop the orphaned tool_use blocks
                    fixed_content = [
                        block for block in content
                        if not (isinstance(block, dict) and block.get("type") == "tool_use")
                    ]
                    if fixed_content:
                        last["content"] = fixed_content
                    else:
                        result.pop()

    # Also check for OpenAI-style tool_calls in assistant messages
    if result:
        last = result[-1]
        if last.get("role") == "assistant" and last.get("tool_calls"):
            # Assistant with tool_calls but no following tool results
            result.pop()

    return result


__all__ = ["truncate_history", "repair_tool_pairs"]
