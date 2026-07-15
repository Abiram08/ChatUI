"""
chatui/agent/loop.py
Unified agent loop — shared tool-round logic for all providers.

Eliminates the duplicated Anthropic/OpenAI loops by using the Provider
Protocol: providers yield Events, the loop handles tool rounds, widget
side-effects, and component detection uniformly.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable

from ..providers.base import (
    EndEvent,
    ErrorEvent,
    TokenEvent,
    ToolCallEvent,
)
from ..runtime.connection import ConnectionState
from ..widgets import Widget, collect_widgets, strip_widgets, widget_payloads

logger = logging.getLogger("chatui")

MAX_TOOL_ROUNDS = 12


async def agent_loop(
    provider: Any,
    conn: ConnectionState,
    send: Callable,
    *,
    registry: Any = None,
    components: Any = None,
    context_fn: Callable | None = None,
    run_tool: Callable | None = None,
    effective_system: Callable | None = None,
) -> None:
    """
    Run the agentic loop with any Provider.

    Handles:
    - Streaming tokens to the client
    - Tool call execution and tool result feedback
    - Widget side-effects (collect/strip)
    - Component detection
    - Stop/cancel
    - Max tool rounds safety limit

    Args:
        provider: A Provider Protocol implementation (yields Events).
        conn: ConnectionState with history, session, stop_event, system_prompt.
        send: Async callable to send messages to the client.
        registry: ToolRegistry for schemas and execution.
        components: ComponentRegistry for component rendering.
        context_fn: Optional context injection function.
        run_tool: Optional async tool runner (preserves session context).
        effective_system: Optional async callable returning the system prompt.
    """
    history = conn.history
    total_in = total_out = 0
    rounds = 0

    while rounds < MAX_TOOL_ROUNDS:
        rounds += 1
        if conn.stop:
            await send({"type": "stopped"})
            return

        # Build system prompt
        if effective_system:
            system = await effective_system(conn)
        else:
            system = conn.system_prompt

        # Get tool schemas in provider-specific format
        tools = None
        if registry and registry.has_tools():
            if hasattr(provider, "_provider_name") and provider._provider_name != "anthropic":
                tools = registry.get_openai_schemas()
            elif hasattr(provider, "_model"):  # Heuristic for Anthropic
                tools = registry.get_schemas()
            else:
                tools = registry.get_schemas()

        # Stream from provider
        full_text = ""
        tool_calls = []
        end_event = None

        try:
            async for event in provider.stream(history, tools, system, conn.stop_event):
                if conn.stop:
                    break
                if isinstance(event, TokenEvent):
                    full_text += event.text
                    await send({"type": "token", "content": event.text})
                elif isinstance(event, ToolCallEvent):
                    tool_calls.append(event)
                elif isinstance(event, EndEvent):
                    end_event = event
                elif isinstance(event, ErrorEvent):
                    await send({"type": "error", "content": event.message})
                    return
        except Exception as e:
            logger.exception("Agent loop stream error")
            await send({"type": "error", "content": str(e)})
            return

        if conn.stop:
            await send({"type": "stopped"})
            return

        if end_event:
            total_in += end_event.input_tokens
            total_out += end_event.output_tokens

        # Component detection
        if components and components.has_any() and full_text.strip():
            result = _check_component(full_text, components)
            if result:
                name, html = result
                await send({"type": "component", "name": name, "html": html})

        # Append assistant message to history
        if full_text or tool_calls:
            if hasattr(provider, "append_assistant"):
                provider.append_assistant(history, full_text, tool_calls)
            else:
                # Fallback: append as plain text
                history.append({"role": "assistant", "content": full_text})

        # Check if we're done (no tool calls or end_turn)
        stop_reason = end_event.stop_reason if end_event else "end_turn"
        if stop_reason != "tool_use" or not tool_calls:
            await send({"type": "end", "usage": {"input": total_in, "output": total_out}})
            return

        # Execute tool calls
        tool_results = []
        for tc in tool_calls:
            await send({
                "type": "tool_call",
                "id": tc.id,
                "name": tc.name,
                "inputs": tc.input,
            })

            # Execute the tool
            if run_tool:
                res = await run_tool(tc.name, tc.input)
            elif registry:
                res = await asyncio.to_thread(registry.execute, tc.name, tc.input)
            else:
                res = {"error": "No tool registry available"}

            # Emit widgets from tool result
            res_str = await _emit_tool_side_effects(send, res, registry)

            await send({
                "type": "tool_result",
                "id": tc.id,
                "name": tc.name,
                "result": res_str,
            })

            # Append tool result to history (provider-specific)
            if hasattr(provider, "append_tool_result"):
                if hasattr(provider, "_provider_name") and provider._provider_name != "anthropic":
                    # OpenAI format: individual tool messages
                    provider.append_tool_result(history, tc.id, res_str)
                else:
                    # Anthropic format: batch tool results
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": res_str,
                    })
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": res_str,
                })

        # For Anthropic, append all tool results as one user message
        if tool_results and not (hasattr(provider, "_provider_name") and provider._provider_name != "anthropic"):
            if hasattr(provider, "append_tool_result"):
                # If it's a list, it's Anthropic-style batch
                import inspect
                sig = inspect.signature(provider.append_tool_result)
                if len(sig.parameters) == 2:
                    provider.append_tool_result(history, tool_results)

        await send({"type": "start_again"})

    await send({
        "type": "error",
        "content": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds.",
    })


async def _emit_tool_side_effects(send: Callable, result: Any, registry: Any = None) -> str:
    """Send widgets if present; return JSON string for the model."""
    widgets = collect_widgets(result)
    if widgets:
        await send({"type": "widgets", "widgets": widget_payloads(widgets)})
    clean = strip_widgets(result)
    if registry:
        return registry.to_json(clean)
    return json.dumps(clean, default=str, ensure_ascii=False)


def _check_component(text: str, components: Any) -> tuple[str, str] | None:
    """Detect component request in text (exact JSON, markdown fences, or prose)."""
    import re

    stripped = (text or "").strip()

    # Try exact JSON first
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict) and "component" in obj:
                name = obj.get("component")
                if name and components.has(name):
                    html = components.render(name, obj.get("data", {}))
                    return name, html
        except (json.JSONDecodeError, TypeError):
            pass

    # Try markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?"component".*?\})\s*```', stripped, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(1))
            if isinstance(obj, dict):
                name = obj.get("component")
                if name and components.has(name):
                    html = components.render(name, obj.get("data", {}))
                    return name, html
        except (json.JSONDecodeError, TypeError):
            pass

    # Try finding JSON anywhere in text
    if "component" in stripped:
        match = re.search(r'\{[^{}]*"component"[^{}]*\}', stripped, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    name = obj.get("component")
                    if name and components.has(name):
                        html = components.render(name, obj.get("data", {}))
                        return name, html
            except (json.JSONDecodeError, TypeError):
                pass

    return None
