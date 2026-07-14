"""
chatui/server.py
FastAPI + WebSocket server with multi-provider streaming and tool calling.

Providers: anthropic | ollama | groq | openai
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .session import (
    SessionState,
    get_current_session,
    reset_current_session,
    set_current_session,
)
from .themes import THEME_NAMES, get_css_vars, get_themes_json
from .tools import ComponentRegistry, ToolRegistry
from .ui.assets import render_html
from .widgets import Widget, collect_widgets, strip_widgets, widget_payloads

load_dotenv()

logger = logging.getLogger("chatui")

VERSION = "0.1.0"

# Soft limits (production defaults)
MAX_MESSAGE_CHARS = 12_000
MAX_HISTORY_TURNS = 40
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB per uploaded file (base64 payload)
MAX_TOOL_ROUNDS = 12

_PROVIDERS = {
    "anthropic": ("claude-sonnet-4-20250514", None),
    "ollama": ("llama3", "http://localhost:11434/v1"),
    "groq": ("llama-3.3-70b-versatile", "https://api.groq.com/openai/v1"),
    "openai": ("gpt-4o", None),
}

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": None,
}

DEFAULT_SYSTEM = """You are a helpful, thoughtful AI assistant.
Use markdown formatting where appropriate:
- **bold** for key terms
- `code` for inline code
- fenced code blocks with language tags
- bullet points for lists
When you have tools available, use them to answer questions accurately.
Be concise and focused."""


class _ToolCall:
    __slots__ = ("id", "name", "input")

    def __init__(self, id: str, name: str, input: dict):
        self.id = id
        self.name = name
        self.input = input


class _RateLimiter:
    """Simple sliding-window limiter (per key)."""

    def __init__(self, max_requests: int = 60, window: float = 60.0):
        self._max = max_requests
        self._window = window
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < self._window]
        if len(hits) >= self._max:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


class ChatUI:
    """
    Production chat UI for Python AI apps.

    Quickstart::

        from chatui import ChatUI
        ChatUI(provider="groq").run()

    Tools / components / events::

        app = ChatUI(provider="groq")

        @app.tool
        def get_weather(city: str) -> dict:
            \"\"\"Current weather for a city.\"\"\"
            return {"city": city, "temp": "22°C"}

        @app.component("chart")
        def chart(data: dict) -> str:
            return f"<b>{data.get('title', 'Chart')}</b>"

        @app.on("button_click")
        def on_click(data: dict):
            return {"clicked": data.get("key")}

        app.run()
    """

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: str = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        system_prompt: str = None,
        title: str = "ChatUI",
        logo: str = "◆",
        subtitle: str = "",
        chips: list = None,
        theme: str = "manuscript",
        model: str = None,
        welcome_title: str = "What shall we<br>work on?",
        open_browser: bool = True,
        cors_origins: list = None,
        rate_limit: int = 0,
        log_level: str = "info",
        auth_key: str = None,
    ):
        p = (provider or "anthropic").lower().strip()
        if p not in _PROVIDERS:
            raise ValueError(
                f"Unknown provider {provider!r}. Choose from: {', '.join(_PROVIDERS)}"
            )

        self.provider = p
        self.host = host
        self.port = int(port)
        self.system_prompt = system_prompt or DEFAULT_SYSTEM
        self.title = title
        self.logo = logo
        self.subtitle = subtitle or ""
        self.chips = list(chips) if chips else []
        self.theme = theme if theme in THEME_NAMES else "manuscript"
        self.welcome_title = welcome_title
        self.open_browser = open_browser
        self.cors_origins = list(cors_origins) if cors_origins is not None else ["*"]
        self.auth_key = auth_key
        self._api_key = api_key

        self._registry = ToolRegistry()
        self._components = ComponentRegistry()
        self._context_fn: Optional[Callable] = None
        self._on_handlers: dict[str, list[Callable]] = {}
        self._rate_limiter = (
            _RateLimiter(max_requests=rate_limit) if rate_limit and rate_limit > 0 else None
        )
        self._fallback_session = SessionState()

        logging.basicConfig(
            level=getattr(logging, (log_level or "info").upper(), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        default_model, base_url = _PROVIDERS[p]
        self.model = model or default_model
        self._base_url = base_url
        self._client = self._build_client(p, api_key, base_url)
        self.app = self._build_fastapi()

    # ── Session (per-connection via contextvars) ──────────────────────

    @property
    def session(self) -> SessionState:
        """Active connection session, or a process-local fallback."""
        # Prefer the connection-bound session; fall back for CLI / pre-WS use.
        current = get_current_session()
        return current if current is not None else self._fallback_session

    # ── Client setup ──────────────────────────────────────────────────

    def _build_client(self, provider: str, api_key: str, base_url: str):
        if provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise ImportError("Install anthropic: pip install anthropic") from e
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            return AsyncAnthropic(api_key=key) if key else None

        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                f"Provider '{provider}' needs the openai package: pip install openai"
            ) from e

        if provider == "ollama":
            return AsyncOpenAI(api_key="ollama", base_url=base_url)

        key = api_key or os.getenv(_ENV_KEYS.get(provider) or "")
        if not key:
            return None
        if provider == "groq":
            return AsyncOpenAI(api_key=key, base_url=base_url)
        return AsyncOpenAI(api_key=key)

    # ── Decorators ────────────────────────────────────────────────────

    def tool(self, fn: Callable = None):
        """Register a Python function as an AI-callable tool."""

        def deco(f: Callable) -> Callable:
            self._registry.register(f)
            return f

        return deco(fn) if fn is not None else deco

    def component(self, name: str):
        """Register an HTML renderer for a named component."""

        def deco(fn: Callable) -> Callable:
            self._components.register(name, fn)
            return fn

        return deco

    def context(self, fn: Callable = None):
        """Inject live data into every model turn."""

        def deco(f: Callable) -> Callable:
            self._context_fn = f
            return f

        return deco(fn) if fn is not None else deco

    def on(self, event: str):
        """
        Handle widget events.

        Register by event name (``button_click``, ``file_upload``, …)
        or by widget ``key``::

            @app.on("button_click")
            def any_button(data): ...

            @app.on("confirm")
            def only_confirm(data): ...
        """

        def deco(fn: Callable) -> Callable:
            self._on_handlers.setdefault(event, []).append(fn)
            return fn

        return deco

    # ── System prompt + components ────────────────────────────────────

    def _effective_system(self) -> str:
        parts = [self.system_prompt]

        if self._context_fn:
            try:
                data = self._context_fn()
                label = (
                    (self._context_fn.__doc__ or self._context_fn.__name__)
                    .strip()
                    .split("\n")[0]
                )
                parts.append(
                    f"\n\n--- Live Context: {label} ---\n"
                    f"{json.dumps(data, default=str, ensure_ascii=False)}"
                )
            except Exception as e:
                logger.exception("Context function failed")
                parts.append(f"\n\n[Context error: {e}]")

        if self._components.has_any():
            names = ", ".join(f'"{n}"' for n in self._components.names())
            parts.append(
                "\n\nWhen you want to render a visual component, reply with ONLY a JSON "
                'object in this exact format: {"component": <name>, "data": {...}} '
                f"where <name> is one of: {names}. "
                "Do not include any other text — just the JSON."
            )

        return "".join(parts)

    def _check_component(self, text: str) -> Optional[tuple[str, str]]:
        stripped = (text or "").strip()
        if not stripped.startswith("{"):
            return None
        try:
            obj = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(obj, dict):
            return None
        name = obj.get("component")
        if name and self._components.has(name):
            html = self._components.render(name, obj.get("data", obj))
            return name, html
        return None

    # ── Tool / widget helpers ─────────────────────────────────────────

    async def _run_tool(self, name: str, inputs: dict) -> Any:
        """Execute a tool off the event loop, preserving session context."""
        session = get_current_session()

        def _call():
            token = set_current_session(session) if session is not None else None
            try:
                return self._registry.execute(name, inputs or {})
            finally:
                if token is not None:
                    reset_current_session(token)

        return await asyncio.to_thread(_call)

    async def _emit_tool_side_effects(self, send: Callable, result: Any) -> str:
        """Send widgets if present; return JSON string for the model."""
        widgets = collect_widgets(result)
        if widgets:
            await send({"type": "widgets", "widgets": widget_payloads(widgets)})
        clean = strip_widgets(result)
        return self._registry.to_json(clean)

    async def _emit_handler_result(self, send: Callable, result: Any) -> None:
        """Stream a simple reply / widgets from an @app.on handler."""
        if result is None:
            return

        widgets = collect_widgets(result)
        if widgets:
            await send({"type": "widgets", "widgets": widget_payloads(widgets)})

        pure_widgets = isinstance(result, Widget) or (
            isinstance(result, (list, tuple))
            and bool(result)
            and all(isinstance(x, Widget) for x in result)
        )
        if pure_widgets:
            return

        clean = strip_widgets(result)
        text = (
            clean
            if isinstance(clean, str)
            else json.dumps(clean, default=str, ensure_ascii=False)
        )
        await send({"type": "start"})
        await send({"type": "token", "content": text})
        await send({"type": "end", "usage": {"input": 0, "output": 0}})

    # ── FastAPI app ───────────────────────────────────────────────────

    def _authorized(self, authorization: str = "", token: str = "") -> bool:
        if not self.auth_key:
            return True
        if authorization == f"Bearer {self.auth_key}":
            return True
        if token and token == self.auth_key:
            return True
        return False

    def _build_fastapi(self) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info(
                "ChatUI %s starting — %s/%s on :%s",
                VERSION,
                self.provider,
                self.model,
                self.port,
            )
            yield
            logger.info("ChatUI shutting down")

        fast = FastAPI(title=self.title, version=VERSION, lifespan=lifespan)

        if self.cors_origins:
            fast.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        if self.auth_key:
            @fast.middleware("http")
            async def auth_middleware(request: Request, call_next):
                # Public: landing page + health (ops). Everything else needs auth.
                if request.url.path in ("/", "/health", "/favicon.ico"):
                    return await call_next(request)
                auth = request.headers.get("Authorization", "")
                token = request.query_params.get("token", "")
                if not self._authorized(auth, token):
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                return await call_next(request)

        if self._rate_limiter:
            @fast.middleware("http")
            async def rate_limit_middleware(request: Request, call_next):
                if request.url.path in ("/ws", "/health"):
                    return await call_next(request)
                client = request.client.host if request.client else "unknown"
                if not self._rate_limiter.check(f"http:{client}"):
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
                "%s %s → %s (%.3fs)",
                request.method,
                request.url.path,
                response.status_code,
                time.time() - start,
            )
            return response

        @fast.get("/")
        async def root():
            # Modular CSS partials + theme vars assembled at serve time (no build step)
            html = render_html(theme_vars=get_css_vars(self.theme))
            # HTML body fields (escape so titles cannot inject markup)
            html = html.replace("{{TITLE}}", _html_esc(self.title))
            html = html.replace("{{LOGO}}", _html_esc(self.logo))
            # welcome_title may intentionally include simple <br> markup
            html = html.replace("{{WELCOME_TITLE}}", self.welcome_title)
            html = html.replace("{{ACTIVE_THEME}}", _html_esc(self.theme))
            # JS string / JSON fields
            html = html.replace("'{{SUBTITLE}}'", json.dumps(self.subtitle))
            html = html.replace("{{SUBTITLE}}", _html_esc(self.subtitle))
            html = html.replace("'{{AUTH_TOKEN}}'", json.dumps(self.auth_key or ""))
            html = html.replace("{{AUTH_TOKEN}}", json.dumps(self.auth_key or "")[1:-1])
            html = html.replace("{{CHIPS_JSON}}", json.dumps(self.chips))
            html = html.replace("{{THEMES_JSON}}", get_themes_json())
            return HTMLResponse(content=html)

        @fast.get("/health")
        async def health():
            return {
                "status": "ok",
                "version": VERSION,
                "provider": self.provider,
                "model": self.model,
                "client_ready": self._client is not None,
                "tools": self._registry.names(),
                "components": self._components.names(),
                "auth": bool(self.auth_key),
            }

        @fast.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket):
            auth = websocket.headers.get("authorization", "")
            token = websocket.query_params.get("token", "")
            if not self._authorized(auth, token):
                await websocket.close(code=4001, reason="Unauthorized")
                return
            await self._handle_ws(websocket)

        return fast

    # ── Agentic loop — Anthropic ──────────────────────────────────────

    async def _loop_anthropic(self, history: list, send: Callable, stop: list) -> None:
        total_in = total_out = 0
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            if stop[0]:
                await send({"type": "stopped"})
                return

            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self._effective_system(),
                "messages": history,
            }
            if self._registry.has_tools():
                kwargs["tools"] = self._registry.get_schemas()

            full_text = ""
            stop_reason = "end_turn"
            tool_uses = []

            try:
                async with self._client.messages.stream(**kwargs) as stream:
                    async for event in stream:
                        if stop[0]:
                            break
                        if (
                            getattr(event, "type", None) == "content_block_delta"
                            and hasattr(event, "delta")
                            and getattr(event.delta, "text", None)
                        ):
                            chunk = event.delta.text
                            full_text += chunk
                            await send({"type": "token", "content": chunk})

                    final = await stream.get_final_message()
                    stop_reason = final.stop_reason
                    total_in += final.usage.input_tokens
                    total_out += final.usage.output_tokens
                    for block in final.content:
                        if block.type == "tool_use":
                            tool_uses.append(block)
            except Exception as e:
                logger.exception("Anthropic stream error")
                await send({"type": "error", "content": str(e)})
                return

            if stop[0]:
                await send({"type": "stopped"})
                return

            if self._components.has_any() and full_text.strip():
                result = self._check_component(full_text)
                if result:
                    name, html = result
                    await send({"type": "component", "name": name, "html": html})

            if full_text or tool_uses:
                content = []
                if full_text:
                    content.append({"type": "text", "text": full_text})
                for tu in tool_uses:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tu.id,
                            "name": tu.name,
                            "input": tu.input,
                        }
                    )
                history.append({"role": "assistant", "content": content})

            if stop_reason != "tool_use" or not tool_uses:
                await send(
                    {"type": "end", "usage": {"input": total_in, "output": total_out}}
                )
                return

            tool_results = []
            for tu in tool_uses:
                await send(
                    {
                        "type": "tool_call",
                        "id": tu.id,
                        "name": tu.name,
                        "inputs": tu.input,
                    }
                )
                res = await self._run_tool(tu.name, tu.input)
                res_str = await self._emit_tool_side_effects(send, res)
                await send(
                    {
                        "type": "tool_result",
                        "id": tu.id,
                        "name": tu.name,
                        "result": res_str,
                    }
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": res_str,
                    }
                )

            history.append({"role": "user", "content": tool_results})
            await send({"type": "start_again"})

        await send(
            {
                "type": "error",
                "content": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds.",
            }
        )

    # ── Agentic loop — OpenAI-compatible ──────────────────────────────

    async def _loop_openai(self, history: list, send: Callable, stop: list) -> None:
        total_in = total_out = 0
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            if stop[0]:
                await send({"type": "stopped"})
                return

            system = self._effective_system()
            messages = [{"role": "system", "content": system}] + history
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "stream": True,
            }
            if self._registry.has_tools():
                kwargs["tools"] = self._registry.get_openai_schemas()
                kwargs["tool_choice"] = "auto"

            full_text = ""
            tc_raw: dict[int, dict] = {}
            finish_reason = "stop"

            try:
                stream = await self._client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if stop[0]:
                        break
                    if getattr(chunk, "usage", None):
                        total_in = getattr(chunk.usage, "prompt_tokens", 0) or total_in
                        total_out = (
                            getattr(chunk.usage, "completion_tokens", 0) or total_out
                        )
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    if delta and delta.content:
                        full_text += delta.content
                        await send({"type": "token", "content": delta.content})
                    if delta and delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tc_raw:
                                tc_raw[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tc_raw[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tc_raw[idx]["name"] += tc.function.name
                                if tc.function.arguments:
                                    tc_raw[idx]["arguments"] += tc.function.arguments
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
            except Exception as e:
                msg = str(e)
                if self.provider == "ollama" and "connection" in msg.lower():
                    msg = (
                        "Cannot connect to Ollama. Start it with:\n"
                        "  ollama serve\n"
                        "  ollama pull llama3"
                    )
                logger.exception("OpenAI-compatible stream error")
                await send({"type": "error", "content": msg})
                return

            if stop[0]:
                await send({"type": "stopped"})
                return

            tool_uses: list[_ToolCall] = []
            for idx in sorted(tc_raw):
                raw = tc_raw[idx]
                try:
                    input_data = json.loads(raw["arguments"] or "{}")
                except json.JSONDecodeError:
                    input_data = {}
                if not isinstance(input_data, dict):
                    input_data = {}
                tool_uses.append(
                    _ToolCall(
                        id=raw["id"] or f"call_{idx}",
                        name=raw["name"],
                        input=input_data,
                    )
                )

            stop_reason = (
                "tool_use"
                if (finish_reason == "tool_calls" and tool_uses)
                else "end_turn"
            )

            if self._components.has_any() and full_text.strip():
                result = self._check_component(full_text)
                if result:
                    name, html = result
                    await send({"type": "component", "name": name, "html": html})

            if full_text or tool_uses:
                asst: dict[str, Any] = {
                    "role": "assistant",
                    "content": full_text or None,
                }
                if tool_uses:
                    asst["tool_calls"] = [
                        {
                            "id": tu.id,
                            "type": "function",
                            "function": {
                                "name": tu.name,
                                "arguments": json.dumps(tu.input),
                            },
                        }
                        for tu in tool_uses
                    ]
                history.append(asst)

            if stop_reason != "tool_use" or not tool_uses:
                await send(
                    {"type": "end", "usage": {"input": total_in, "output": total_out}}
                )
                return

            for tu in tool_uses:
                await send(
                    {
                        "type": "tool_call",
                        "id": tu.id,
                        "name": tu.name,
                        "inputs": tu.input,
                    }
                )
                res = await self._run_tool(tu.name, tu.input)
                res_str = await self._emit_tool_side_effects(send, res)
                await send(
                    {
                        "type": "tool_result",
                        "id": tu.id,
                        "name": tu.name,
                        "result": res_str,
                    }
                )
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tu.id,
                        "content": res_str,
                    }
                )

            await send({"type": "start_again"})

        await send(
            {
                "type": "error",
                "content": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds.",
            }
        )

    async def _agentic_loop(self, history: list, send: Callable, stop: list) -> None:
        if self.provider == "anthropic":
            await self._loop_anthropic(history, send, stop)
        else:
            await self._loop_openai(history, send, stop)

    # ── WebSocket handler ─────────────────────────────────────────────

    async def _handle_ws(self, websocket: WebSocket) -> None:
        await websocket.accept()
        history: list = []
        stop = [False]
        generating = False
        session = SessionState()
        client_host = websocket.client.host if websocket.client else "unknown"

        async def send(payload: dict) -> None:
            await websocket.send_text(json.dumps(payload, default=str))

        token = set_current_session(session)
        try:
            await send(
                {
                    "type": "config",
                    "provider": self.provider,
                    "model": self.model,
                    "session": session.id,
                    "version": VERSION,
                }
            )

            if self._registry.has_tools():
                await send(
                    {
                        "type": "tools_ready",
                        "tools": [
                            {
                                "name": s["name"],
                                "description": s.get("description", ""),
                            }
                            for s in self._registry.get_schemas()
                        ],
                    }
                )

            if self._components.has_any():
                await send(
                    {
                        "type": "components_ready",
                        "components": self._components.names(),
                    }
                )

            await send({"type": "session_state", "data": session.to_dict()})

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
                    history = []
                    stop[0] = True
                    await send({"type": "cleared"})
                    continue

                if action == "stop":
                    stop[0] = True
                    continue

                if action == "update_system":
                    prompt = (payload.get("prompt") or "").strip()
                    if prompt:
                        self.system_prompt = prompt[:20_000]
                        await send({"type": "system_updated"})
                    continue

                if action == "set_session":
                    key = payload.get("key")
                    if key is not None and isinstance(key, str) and len(key) < 200:
                        session[key] = payload.get("value")
                        await send(
                            {
                                "type": "session_updated",
                                "key": key,
                                "value": session.get(key),
                            }
                        )
                    continue

                if action == "get_session":
                    await send({"type": "session_state", "data": session.to_dict()})
                    continue

                if action == "widget_event":
                    await self._handle_widget_event(payload, send, session)
                    continue

                if action == "regenerate":
                    if generating:
                        await send(
                            {
                                "type": "error",
                                "content": "Already generating a response.",
                            }
                        )
                        continue
                    while history:
                        last = history[-1]
                        if last.get("role") == "user" and isinstance(
                            last.get("content"), str
                        ):
                            break
                        history.pop()
                    if not history:
                        continue
                    if not self._rate_ok(client_host, send):
                        continue
                    stop[0] = False
                    generating = True
                    try:
                        if not self._client:
                            await send({"type": "start"})
                            await send(
                                {
                                    "type": "error",
                                    "content": _no_key_msg(self.provider),
                                }
                            )
                        else:
                            await send({"type": "start"})
                            await self._agentic_loop(history, send, stop)
                    finally:
                        generating = False
                    continue

                # chat / default message path
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

                if generating:
                    await send(
                        {
                            "type": "error",
                            "content": "Please wait for the current response to finish.",
                        }
                    )
                    continue

                if not self._rate_ok(client_host, send):
                    continue

                stop[0] = False
                history.append({"role": "user", "content": user_msg})
                if len(history) > MAX_HISTORY_TURNS * 2:
                    history = history[-(MAX_HISTORY_TURNS * 2) :]

                generating = True
                try:
                    if not self._client:
                        await send({"type": "start"})
                        await send(
                            {"type": "error", "content": _no_key_msg(self.provider)}
                        )
                    else:
                        await send({"type": "start"})
                        await self._agentic_loop(history, send, stop)
                finally:
                    generating = False

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected (%s)", session.id)
        except Exception as err:
            logger.exception("WebSocket error")
            try:
                await send({"type": "error", "content": str(err)})
            except Exception:
                pass
        finally:
            reset_current_session(token)

    async def _handle_widget_event(
        self, payload: dict, send: Callable, session: SessionState
    ) -> None:
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

        # Guard large file uploads
        files = data.get("files")
        if isinstance(files, list):
            safe_files = []
            for f in files[:10]:
                if not isinstance(f, dict):
                    continue
                content = f.get("content") or ""
                # Rough base64 size check
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

        # Handlers for event name AND widget key (README + per-button keys)
        handlers: list[Callable] = []
        seen = set()
        for key in (event_type, widget_key):
            if not key:
                continue
            for h in self._on_handlers.get(key, []):
                if id(h) not in seen:
                    seen.add(id(h))
                    handlers.append(h)

        if not handlers:
            logger.debug("No handlers for event=%s key=%s", event_type, widget_key)
            return

        token = set_current_session(session)
        try:
            for handler in handlers:
                try:
                    result = handler(data)
                    if asyncio.iscoroutine(result):
                        result = await result
                    await self._emit_handler_result(send, result)
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

    async def _rate_ok(self, client_host: str, send: Callable) -> bool:
        if not self._rate_limiter:
            return True
        if self._rate_limiter.check(f"ws:{client_host}"):
            return True
        await send(
            {
                "type": "error",
                "content": "Rate limit exceeded. Please wait a moment.",
            }
        )
        return False

    # ── Run ───────────────────────────────────────────────────────────

    def run(self, host: str = None, port: int = None, **kwargs):
        """Start the ChatUI server (blocking)."""
        h = host or self.host
        p = port or self.port

        if self.open_browser:
            import threading
            import webbrowser

            def _open():
                time.sleep(1.0)
                webbrowser.open(f"http://localhost:{p}")

            threading.Thread(target=_open, daemon=True).start()

        tools = self._registry.names()
        comps = self._components.names()

        print(f"\n  ChatUI v{VERSION}  |  {self.provider} / {self.model}  |  {self.theme}")
        print(f"  Running at    http://localhost:{p}")
        print(f"  Health check  http://localhost:{p}/health")
        if self.auth_key:
            print("  Auth          enabled (Bearer / ?token=)")
        if self._rate_limiter:
            print(f"  Rate limit    {self._rate_limiter._max} req/min")
        if tools:
            print(f"  Tools         {', '.join(tools)}")
        if comps:
            print(f"  Components    {', '.join(comps)}")
        if self._context_fn:
            print(f"  Context       {self._context_fn.__name__}()")
        if self._on_handlers:
            for evt, handlers in self._on_handlers.items():
                names = ", ".join(h.__name__ for h in handlers)
                print(f"  On[{evt}]      {names}")
        if self._client is None and self.provider != "ollama":
            print(f"  Warning       no API key — set {_ENV_KEYS.get(self.provider)}")
        print()

        uvicorn.run(self.app, host=h, port=p, log_level="warning", **kwargs)


def _no_key_msg(provider: str) -> str:
    env = _ENV_KEYS.get(provider)
    if provider == "ollama":
        return (
            "Ollama client is not ready. Install and start Ollama:\n"
            "  ollama pull llama3\n"
            "  ollama serve"
        )
    return (
        f"No API key for provider '{provider}'. "
        f"Pass api_key=... to ChatUI() or set {env}."
    )


def _html_esc(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
