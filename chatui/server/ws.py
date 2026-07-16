"""
chatui/server/ws.py
WebSocket handler — connection lifecycle, agent loop, reply loop, widget events.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from .._constants import (
    MAX_FILE_BYTES,
    MAX_MESSAGE_CHARS,
    VERSION,
    _no_key_msg,
)
from ..exceptions import ChatUIError
from ..runtime.connection import ConnectionState
from ..runtime.history import truncate_history
from ..session import (
    get_current_session,
    reset_current_session,
    set_current_session,
)
from ..widgets import Widget, collect_widgets, widget_payloads

logger = logging.getLogger("chatui")


async def handle_websocket(app, websocket: WebSocket) -> None:
    """Handle a WebSocket connection lifecycle."""
    await websocket.accept()

    conn = ConnectionState(
        system_prompt=app.system_prompt,
    )
    client_host = websocket.client.host if websocket.client else "unknown"

    async def send(payload: dict) -> None:
        await websocket.send_text(json.dumps(payload, default=str))

    token = set_current_session(conn.session)
    try:
        await send(
            {
                "type": "config",
                "provider": app.provider,
                "model": app.model,
                "session": conn.session.id,
                "version": VERSION,
                "protocol_version": 1,
                "lite": app.lite,
                "allow_system_prompt": app.allow_client_system_prompt,
                "history_turns": app.history_turns,
                "max_message_chars": MAX_MESSAGE_CHARS,
            }
        )

        if app._registry.has_tools():
            tools_list = [
                {"name": s["name"], "description": s.get("description", "")}
                for s in app._registry.get_schemas()
            ]
            await send({"type": "tools_ready", "tools": tools_list})
            if not app.chips:
                app.chips = [
                    f"Try: {t['description'][:60]}"
                    for t in tools_list[:3]
                ]

        if app._components.has_any():
            await send(
                {
                    "type": "components_ready",
                    "components": app._components.names(),
                }
            )

        await send({"type": "session_state", "data": conn.session.to_dict()})

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await send({"type": "error", "content": "Invalid JSON message."})
                continue

            if not isinstance(payload, dict):
                continue

            action = payload.get("action")

            if action == "clear":
                conn.clear_history()
                conn.reset_stop()
                await send({"type": "cleared"})
                continue

            if action == "set_history":
                # Restore client-side conversation so continue/regenerate have context.
                if conn.generating:
                    await send(
                        {
                            "type": "error",
                            "content": "Cannot load history while generating.",
                        }
                    )
                    continue
                messages = payload.get("messages")
                if not isinstance(messages, list):
                    await send(
                        {"type": "error", "content": "Invalid history payload."}
                    )
                    continue
                max_msgs = max(2, int(app.history_turns or 40) * 2 + 4)
                cleaned: list[dict] = []
                for m in messages[:max_msgs]:
                    if not isinstance(m, dict):
                        continue
                    role = m.get("role")
                    content = m.get("content")
                    if role not in ("user", "assistant"):
                        continue
                    if not isinstance(content, str):
                        continue
                    content = content.strip()
                    if not content:
                        continue
                    cleaned.append(
                        {
                            "role": role,
                            "content": content[:MAX_MESSAGE_CHARS],
                        }
                    )
                conn.history = cleaned
                conn.reset_stop()
                await send({"type": "history_set", "count": len(cleaned)})
                continue

            if action == "stop":
                conn.request_stop()
                continue

            if action == "update_system":
                if not app.allow_client_system_prompt:
                    await send(
                        {"type": "error", "content": "System prompt updates are disabled."}
                    )
                    continue
                # Empty prompt resets to the app default for this connection.
                prompt = (payload.get("prompt") or "").strip()
                if prompt:
                    conn.system_prompt = prompt[:20_000]
                else:
                    conn.system_prompt = app.system_prompt
                await send({"type": "system_updated"})
                continue

            if action == "set_session":
                key = payload.get("key")
                if key is not None and isinstance(key, str) and len(key) < 200:
                    conn.session[key] = payload.get("value")
                    await send(
                        {
                            "type": "session_updated",
                            "key": key,
                            "value": conn.session.get(key),
                        }
                    )
                continue

            if action == "get_session":
                await send({"type": "session_state", "data": conn.session.to_dict()})
                continue

            if action == "widget_event":
                await _handle_widget_event(app, payload, send, conn)
                continue

            if action == "regenerate":
                if conn.generating:
                    await send(
                        {"type": "error", "content": "Already generating a response."}
                    )
                    continue
                conn.pop_to_last_user_message()
                if not conn.history:
                    continue
                if not await _rate_ok(app, client_host, send):
                    continue
                conn.reset_stop()
                conn.generating = True
                try:
                    if not app._provider and app._reply_fn is None:
                        await send({"type": "start"})
                        await send(
                            {"type": "error", "content": _no_key_msg(app.provider)}
                        )
                    else:
                        await send({"type": "start"})
                        await _agentic_loop(app, conn, send)
                finally:
                    conn.generating = False
                continue

            user_msg = (payload.get("message") or "").strip()
            if not user_msg:
                continue

            if len(user_msg) > MAX_MESSAGE_CHARS:
                await send(
                    {
                        "type": "error",
                        "content": (
                            f"Message too long "
                            f"({len(user_msg)} chars, max {MAX_MESSAGE_CHARS})."
                        ),
                    }
                )
                continue

            if conn.generating:
                await send(
                    {"type": "error", "content": "Please wait for the current response to finish."}
                )
                continue

            if not await _rate_ok(app, client_host, send):
                continue

            conn.reset_stop()
            conn.history.append({"role": "user", "content": user_msg})

            conn.history = truncate_history(conn.history, app.history_turns)

            conn.generating = True
            try:
                if not app._provider and app._reply_fn is None:
                    await send({"type": "start"})
                    await send(
                        {"type": "error", "content": _no_key_msg(app.provider)}
                    )
                else:
                    await send({"type": "start"})
                    await _agentic_loop(app, conn, send)
            finally:
                conn.generating = False

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected (%s)", conn.session.id)
    except ChatUIError as e:
        logger.error("ChatUI error: %s", e)
        try:
            await send({"type": "error", "content": str(e)})
        except Exception:
            pass
    except Exception as err:
        logger.exception("WebSocket error")
        try:
            await send({"type": "error", "content": "Internal error. Check server logs."})
        except Exception:
            pass
    finally:
        reset_current_session(token)


async def _loop_reply(app, conn: ConnectionState, message: str, send) -> None:
    """Handle a message using a user-supplied reply function."""
    fn = app._reply_fn
    session = conn.session

    await send({"type": "start"})
    try:
        if inspect.isasyncgenfunction(fn):
            async for chunk in fn(message, session):
                if conn.stop:
                    break
                if isinstance(chunk, str):
                    await send({"type": "token", "content": chunk})
                elif isinstance(chunk, Widget):
                    await send({"type": "widgets", "widgets": [chunk.to_payload()]})
        elif asyncio.iscoroutinefunction(fn):
            result = await fn(message, session)
            if isinstance(result, str):
                await send({"type": "token", "content": result})
            else:
                await app._emit_handler_result(send, result)
        else:
            result = await asyncio.to_thread(fn, message, session)
            if isinstance(result, str):
                await send({"type": "token", "content": result})
            else:
                await app._emit_handler_result(send, result)
    except Exception as e:
        logger.exception("Reply function error")
        await send({"type": "error", "content": f"Reply error: {e}"})

    await send({"type": "end", "usage": {"input": 0, "output": 0}})


async def _agentic_loop(app, conn: ConnectionState, send) -> None:
    """Dispatch to unified agent loop or custom reply."""
    if app._reply_fn is not None:
        message = conn.history[-1]["content"] if conn.history else ""
        await _loop_reply(app, conn, message, send)
        return

    from ..agent.loop import agent_loop

    async def hooked_send(payload):
        msg_type = payload.get("type")
        if msg_type == "token":
            await app._run_hooks("on_token", payload.get("content", ""))
        elif msg_type == "tool_call":
            await app._run_hooks("on_tool", payload.get("name", ""), payload.get("inputs", {}))
        elif msg_type == "error":
            await app._run_hooks("on_error", payload.get("content", ""))
        elif msg_type == "end":
            await app._run_hooks("on_end", payload.get("usage", {}))
        await send(payload)

    await agent_loop(
        provider=app._provider,
        conn=conn,
        send=hooked_send,
        registry=app._registry,
        components=app._components,
        context_fn=app._context_fn,
        run_tool=app._run_tool,
        effective_system=app._effective_system,
    )


async def _handle_widget_event(app, payload: dict, send, conn) -> None:
    """Handle a widget event from the client."""
    event_type = (payload.get("event") or "").strip()
    widget_key = payload.get("key") or ""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    data = {
        **data,
        "key": widget_key or data.get("key", ""),
        "value": payload.get("value", data.get("value")),
        "widget_id": payload.get("widget_id", ""),
        "event": event_type,
    }

    files = data.get("files")
    if isinstance(files, list):
        safe_files = []
        for f in files[:10]:
            if not isinstance(f, dict):
                continue
            content = f.get("content") or ""
            if isinstance(content, str) and len(content) > MAX_FILE_BYTES * 1.4:
                await send(
                    {
                        "type": "error",
                        "content": (
                            f"File '{f.get('name', '?')}' is too large "
                            f"(max {MAX_FILE_BYTES // (1024 * 1024)} MB)."
                        ),
                    }
                )
                return
            safe_files.append(
                {
                    "name": str(f.get("name", ""))[:500],
                    "type": str(f.get("type", ""))[:200],
                    "size": f.get("size", 0),
                    "content": content,
                }
            )
        data["files"] = safe_files

    handlers: list = []
    seen = set()
    for key in (event_type, widget_key):
        if not key:
            continue
        for h in app._on_handlers.get(key, []):
            if id(h) not in seen:
                seen.add(id(h))
                handlers.append(h)

    if not handlers:
        logger.debug("No handlers for event=%s key=%s", event_type, widget_key)
        return

    token = set_current_session(conn.session)
    try:
        for handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    result = await result
                await app._emit_handler_result(send, result)
            except Exception as e:
                logger.exception("Event handler %s failed", handler.__name__)
                await send(
                    {
                        "type": "error",
                        "content": f"Handler error ({handler.__name__}): {e}",
                    }
                )
    finally:
        reset_current_session(token)


async def _rate_ok(app, client_host: str, send) -> bool:
    if not app._rate_limiter:
        return True
    if app._rate_limiter.check(f"ws:{client_host}"):
        return True
    await send(
        {"type": "error", "content": "Rate limit exceeded. Please wait a moment."}
    )
    return False
