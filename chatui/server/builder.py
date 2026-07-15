"""
chatui/server/builder.py
FastAPI application builder — routes, middleware, static files.
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .._constants import VERSION, _html_esc, _sanitize_welcome_title
from ..themes import get_css_vars, get_themes_json
from ..ui.assets import render_html

logger = logging.getLogger("chatui")


def build_fastapi_app(app_instance):
    """
    Build the FastAPI application for a ChatUI instance.

    Sets up:
    - Static file serving (vendored JS/CSS)
    - CORS middleware
    - Optional auth middleware
    - Optional rate limit middleware
    - Logging middleware
    - GET / route (HTML shell)
    - GET /health route
    - WebSocket /ws route
    """
    from .ws import handle_websocket

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "ChatUI %s starting — %s/%s on :%s",
            VERSION,
            app_instance.provider,
            app_instance.model,
            app_instance.port,
        )
        yield
        logger.info("ChatUI shutting down")

    fast = FastAPI(title=app_instance.title, version=VERSION, lifespan=lifespan)

    from fastapi.staticfiles import StaticFiles
    from pathlib import Path

    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    vendor_dir = ui_dir / "vendor"
    js_dir = ui_dir / "js"
    if vendor_dir.is_dir():
        fast.mount("/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")
    if js_dir.is_dir():
        fast.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    if app_instance.cors_origins:
        fast.add_middleware(
            CORSMiddleware,
            allow_origins=app_instance.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if app_instance.auth_key:
        @fast.middleware("http")
        async def auth_middleware(request: Request, call_next):
            if request.url.path in ("/", "/health", "/favicon.ico"):
                return await call_next(request)
            auth = request.headers.get("Authorization", "")
            token = request.query_params.get("token", "")
            if not app_instance._authorized(auth, token):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return await call_next(request)

    if app_instance._rate_limiter:
        @fast.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            if request.url.path in ("/ws", "/health"):
                return await call_next(request)
            client = request.client.host if request.client else "unknown"
            if not app_instance._rate_limiter.check(f"http:{client}"):
                return JSONResponse(
                    {"detail": "Too many requests. Slow down."},
                    status_code=429,
                )
            return await call_next(request)

    @fast.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        logger.debug(
            "%s %s -> %s (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            time.time() - start,
        )
        return response

    @fast.get("/")
    async def root():
        html = render_html(theme_vars=get_css_vars(app_instance.theme))
        html = html.replace("{{TITLE}}", _html_esc(app_instance.title))
        html = html.replace("{{LOGO}}", _html_esc(app_instance.logo))
        html = html.replace("{{WELCOME_TITLE}}", _sanitize_welcome_title(app_instance.welcome_title))
        html = html.replace("{{ACTIVE_THEME}}", _html_esc(app_instance.theme))
        html = html.replace("'{{SUBTITLE}}'", json.dumps(app_instance.subtitle))
        html = html.replace("{{SUBTITLE}}", _html_esc(app_instance.subtitle))
        html = html.replace("'{{AUTH_TOKEN}}'", "''")
        html = html.replace("{{AUTH_TOKEN}}", "")
        html = html.replace("{{CHIPS_JSON}}", json.dumps(app_instance.chips))
        themes_subset = getattr(app_instance, "_themes_subset", None)
        if app_instance.lite and not themes_subset:
            themes_subset = [app_instance.theme]
        html = html.replace("{{THEMES_JSON}}", get_themes_json(themes_subset))
        return HTMLResponse(content=html)

    @fast.get("/health")
    async def health():
        is_prod = os.environ.get("CHATUI_ENV") == "production"
        if is_prod:
            return {"status": "ok"}
        return {
            "status": "ok",
            "version": VERSION,
            "provider": app_instance.provider,
            "model": app_instance.model,
            "client_ready": app_instance._provider is not None,
            "tools": app_instance._registry.names(),
            "components": app_instance._components.names(),
            "auth": bool(app_instance.auth_key),
        }

    @fast.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        auth = websocket.headers.get("authorization", "")
        token = websocket.query_params.get("token", "")
        if not app_instance._authorized(auth, token):
            await websocket.close(code=4001, reason="Unauthorized")
            return
        await handle_websocket(app_instance, websocket)

    return fast
