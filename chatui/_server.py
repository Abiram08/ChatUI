"""
chatui/_server.py

Core server implementation. Provides the ChatUI class that manages a
FastAPI application with WebSocket-based chat, theming, and layout
rendering. Designed to be embedded or run standalone.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("chatui")

MessageHandler = Callable[[str, dict[str, Any]], Any]


def _html_esc(s: str) -> str:
    """Escape a string for safe HTML embedding."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


class ChatUI:
    """A chat UI server with theming, layouts, and WebSocket-based messaging.

    Parameters
    ----------
    reply : Callable
        The message handler. Can be:
        - A sync function: ``def handler(message: str, session: dict) -> str``
        - An async function: ``async def handler(message: str, session: dict) -> str``
        - A sync generator: ``def handler(message: str, session: dict) -> Generator[str]``
        - An async generator: ``async def handler(message: str, session: dict) -> AsyncGenerator[str]``
    title : str, optional
        Page title and sidebar heading, by default "Chat"
    subtitle : str, optional
        Subtitle shown below the welcome heading, by default ""
    logo : str, optional
        Logo character shown in the sidebar, by default "◆"
    welcome_title : str, optional
        Hero heading on the welcome screen, by default "What can I help with?"
    layout : str, optional
        One of "sidebar" or "tabs", by default "sidebar"
    theme : str, optional
        One of "dark", "light", "sepia", "slate", by default "dark"
    chips : list[str] | None, optional
        Suggested prompt chips shown on the welcome screen
    host : str, optional
        Bind address, by default "0.0.0.0"
    port : int, optional
        Bind port, by default 8000
    """

    def __init__(
        self,
        *,
        reply: MessageHandler,
        title: str = "Chat",
        subtitle: str = "",
        logo: str = "\u25c6",
        welcome_title: str = "What can I help with?",
        layout: str = "sidebar",
        theme: str = "dark",
        chips: list[str] | None = None,
        host: str = "0.0.0.0",
        port: int = 8000,
    ) -> None:
        VALID_LAYOUTS = ("sidebar", "tabs")
        VALID_THEMES = ("dark", "light", "sepia", "slate")

        if layout not in VALID_LAYOUTS:
            raise ValueError(f"layout must be one of {VALID_LAYOUTS}, got {layout!r}")
        if theme not in VALID_THEMES:
            raise ValueError(f"theme must be one of {VALID_THEMES}, got {theme!r}")

        self.reply = reply
        self.title = title
        self.subtitle = subtitle
        self.logo = logo
        self.welcome_title = welcome_title
        self.layout = layout
        self.theme = theme
        self.chips = chips or []
        self.host = host
        self.port = port

    def _build_html_response(self) -> str:
        """Assemble the full HTML document from the template and theme CSS."""
        from .themes import get_css_vars, get_themes_json
        from .ui.assets import render_html

        html = render_html(theme_vars=get_css_vars(self.theme))
        html = html.replace("{{TITLE}}", _html_esc(self.title))
        html = html.replace("{{LOGO}}", _html_esc(self.logo))
        html = html.replace("{{WELCOME_TITLE}}", _html_esc(self.welcome_title))
        html = html.replace("{{SUBTITLE}}", _html_esc(self.subtitle))
        html = html.replace("{{CHIPS_JSON}}", json.dumps(self.chips))
        html = html.replace("{{LAYOUT}}", self.layout)
        html = html.replace("{{THEMES_JSON}}", get_themes_json())
        html = html.replace("{{ACTIVE_THEME}}", _html_esc(self.theme))
        return html

    def _build_fastapi_app(self) -> FastAPI:
        """Create and return the FastAPI application with routes and middleware."""
        fast = FastAPI(title=self.title)

        ui_dir = Path(__file__).resolve().parent / "ui"
        vendor_dir = ui_dir / "vendor"
        js_dir = ui_dir / "js"

        if vendor_dir.is_dir():
            fast.mount("/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")
        if js_dir.is_dir():
            fast.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

        @fast.get("/")
        async def root() -> HTMLResponse:
            return HTMLResponse(content=self._build_html_response())

        @fast.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @fast.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            session: dict[str, Any] = {}
            try:
                await websocket.send_json({
                    "type": "config",
                    "label": f"chatui \u00b7 {self.title}",
                })
                while True:
                    data = await websocket.receive_json()
                    action = data.get("action", "")
                    if action == "chat":
                        message = data.get("message", "")
                        await self._stream_reply(websocket, message, session)
                    elif action == "regenerate":
                        await self._stream_reply(websocket, "", session)
                    elif action == "set_history":
                        session["history"] = self._normalize_history(
                            data.get("messages", [])
                        )
                    elif action == "clear":
                        session = {}
                    elif action == "stop":
                        pass
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.exception("WebSocket error")
                try:
                    await websocket.send_json({"type": "error", "content": str(exc)})
                except Exception:
                    pass

        return fast

    async def _stream_reply(
        self, ws: WebSocket, message: str, session: dict[str, Any]
    ) -> None:
        """Call the reply handler and stream tokens back over the WebSocket."""
        reply = self.reply
        history = session.setdefault("history", [])
        if message:
            history.append({"role": "user", "content": message})
        await ws.send_json({"type": "start"})
        full_reply = ""

        try:
            if inspect.isasyncgenfunction(reply):
                async for chunk in reply(message, session):
                    if isinstance(chunk, str):
                        full_reply += chunk
                        await ws.send_json({"type": "token", "content": chunk})
            elif inspect.isgeneratorfunction(reply):
                for chunk in reply(message, session):
                    if isinstance(chunk, str):
                        full_reply += chunk
                        await ws.send_json({"type": "token", "content": chunk})
                    await asyncio.sleep(0)
            elif asyncio.iscoroutinefunction(reply):
                result = await reply(message, session)
                if isinstance(result, str) and result:
                    full_reply = result
                    await ws.send_json({"type": "token", "content": result})
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, reply, message, session)
                if isinstance(result, str) and result:
                    full_reply = result
                    await ws.send_json({"type": "token", "content": result})
        except Exception as exc:
            logger.exception("Reply handler error")
            await ws.send_json({"type": "error", "content": str(exc)})
            await ws.send_json({"type": "end"})
            return

        if full_reply:
            history.append({"role": "assistant", "content": full_reply})
        await ws.send_json({"type": "end"})

    @staticmethod
    def _normalize_history(messages: Any) -> list[dict[str, str]]:
        if not isinstance(messages, list):
            return []
        normalized: list[dict[str, str]] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str):
                normalized.append({"role": role, "content": content})
        return normalized

    @property
    def app(self) -> FastAPI:
        """The underlying FastAPI application. Built lazily."""
        if not hasattr(self, "_app"):
            self._app = self._build_fastapi_app()
        return self._app

    @app.setter
    def app(self, value: FastAPI) -> None:
        self._app = value

    def run(
        self, host: str | None = None, port: int | None = None
    ) -> None:
        """Start the Uvicorn server (blocking).

        Parameters
        ----------
        host : str, optional
            Override the bind address
        port : int, optional
            Override the bind port
        """
        import uvicorn
        h = host or self.host
        p = port or self.port
        print(f"\n  ChatUI v0.3.0  |  layout={self.layout}  theme={self.theme}")
        print(f"  Running at     http://localhost:{p}\n")
        uvicorn.run(self.app, host=h, port=p, log_level="warning")
