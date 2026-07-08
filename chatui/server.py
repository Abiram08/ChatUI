"""
chatui/server.py
FastAPI server, WebSocket handler, multi-provider AI streaming with tool calling.

Supported providers:
  anthropic  — Claude (best tool calling)   pip install chatui
  ollama     — Local LLMs, zero cost        brew install ollama && ollama pull llama3
  groq       — Free cloud inference         console.groq.com (30-second signup)
  openai     — GPT-4o and friends           platform.openai.com
"""
import os
import json
import time
import logging
import asyncio
import uvicorn
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Optional

from .tools import ToolRegistry, ComponentRegistry
from .themes import get_css_vars, get_themes_json, THEME_NAMES
from .session import SessionState
from .widgets import Widget

load_dotenv()

logger = logging.getLogger("chatui")

UI_PATH = Path(__file__).parent / "ui" / "index.html"

# ── Provider catalogue ────────────────────────────────────────────────────────

_PROVIDERS = {
    "anthropic": ("claude-sonnet-4-20250514", None),
    "ollama":    ("llama3",                    "http://localhost:11434/v1"),
    "groq":      ("llama3-8b-8192",            "https://api.groq.com/openai/v1"),
    "openai":    ("gpt-4o",                    None),
}

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq":      "GROQ_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "ollama":    None,
}

DEFAULT_SYSTEM = """You are a helpful, thoughtful AI assistant.
Use markdown formatting where appropriate:
- **bold** for key terms
- `code` for inline code
- fenced code blocks with language tags
- bullet points for lists
When you have tools available, use them to answer questions accurately.
Be concise and focused."""

# ── Small helper for OpenAI-style tool call accumulation ─────────────────────

class _ToolCall:
    __slots__ = ("id", "name", "input")
    def __init__(self, id: str, name: str, input: dict):
        self.id    = id
        self.name  = name
        self.input = input


# ── Rate limiter ─────────────────────────────────────────────────────────────

class _RateLimiter:
    def __init__(self, max_requests: int = 20, window: float = 60.0):
        self._max = max_requests
        self._window = window
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        hits = self._hits.get(key, [])
        hits = [t for t in hits if now - t < self._window]
        if len(hits) >= self._max:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


# ── ChatUI ───────────────────────────────────────────────────────────────────

class ChatUI:
    """
    A production-quality chat interface for Python AI applications.

    Quickstart:
        from chatui import ChatUI

        app = ChatUI()           # Anthropic (set ANTHROPIC_API_KEY)
        app.run()

    Free / local:
        app = ChatUI(provider="ollama", model="llama3")
        app.run()

    Tool calling:
        @app.tool
        def get_weather(city: str) -> dict:
            "Get current weather for a city."
            return {"temp": 28, "city": city}

    Custom components:
        @app.component("chart")
        def render_chart(data: dict) -> str:
            return "<canvas>...</canvas>"

    Live context:
        @app.context
        def my_data():
            "Current dataset."
            return df.to_dict()

    Session state:
        @app.tool
        def remember(key: str, value: str):
            app.session[key] = value
            return {"ok": True}

    Widgets:
        from chatui.widgets import button, text_input, progress

        @app.tool
        def ask_confirm(message: str):
            return button("Confirm", key="confirm"), button("Cancel", key="cancel", variant="danger")
    """

    def __init__(
        self,
        provider:       str  = "anthropic",
        api_key:        str  = None,
        host:           str  = "0.0.0.0",
        port:           int  = 8000,
        system_prompt:  str  = None,
        title:          str  = "ChatUI",
        logo:           str  = "◆",
        subtitle:       str  = "",
        chips:          list = None,
        theme:          str  = "manuscript",
        model:          str  = None,
        welcome_title:  str  = "What shall we<br>work on?",
        open_browser:   bool = True,
        cors_origins:   list = None,
        rate_limit:     int  = 0,
        log_level:      str  = "info",
        auth_key:       str  = None,
    ):
        p = provider.lower()
        if p not in _PROVIDERS:
            raise ValueError(
                f"Unknown provider {p!r}. Choose from: {', '.join(_PROVIDERS)}"
            )

        self.provider      = p
        self.host          = host
        self.port          = port
        self.system_prompt = system_prompt or DEFAULT_SYSTEM
        self.title         = title
        self.logo          = logo
        self.subtitle      = subtitle
        self.chips         = chips
        self.theme         = theme if theme in THEME_NAMES else "manuscript"
        self.welcome_title = welcome_title
        self.open_browser  = open_browser
        self.cors_origins  = cors_origins or ["*"]
        self.auth_key      = auth_key
        self._registry     = ToolRegistry()
        self._components   = ComponentRegistry()
        self._context_fn   = None
        self._on_handlers: dict[str, list] = {}
        self._rate_limiter = _RateLimiter(max_requests=rate_limit) if rate_limit > 0 else None
        self._session_proto = SessionState()

        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        default_model, base_url = _PROVIDERS[p]
        self.model = model or default_model

        self._client = self._build_client(p, api_key, base_url)
        self.app     = self._build_fastapi()

    # ── Session access ─────────────────────────────────────────────────

    @property
    def session(self) -> SessionState:
        return self._session_proto

    # ── Client setup ──────────────────────────────────────────────────

    def _build_client(self, provider: str, api_key: str, base_url: str):
        if provider == "anthropic":
            from anthropic import Anthropic
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            return Anthropic(api_key=key) if key else None

        try:
            from openai import OpenAI as _OAI
        except ImportError:
            raise ImportError(
                f"Provider '{provider}' requires the openai package. "
                "Install it with:  pip install openai"
            )

        if provider == "ollama":
            return _OAI(api_key="ollama", base_url=base_url)

        key = api_key or os.getenv(_ENV_KEYS.get(provider, ""))
        if provider == "groq":
            return _OAI(api_key=key or "missing", base_url=base_url)

        return _OAI(api_key=key) if key else None

    # ── Decorators ────────────────────────────────────────────────────

    def tool(self, fn):
        """Register a Python function as an AI tool.

        @app.tool
        def search(query: str) -> dict:
            "Search the web."
            ...
        """
        self._registry.register(fn)
        return fn

    def component(self, name: str):
        """Register an HTML renderer for a named component.

        When the AI responds with {"component": "chart", "data": {...}},
        ChatUI calls this function and injects the returned HTML into the chat.

        @app.component("chart")
        def render_chart(data: dict) -> str:
            return "<canvas id='c'></canvas><script>...</script>"
        """
        def decorator(fn):
            self._components.register(name, fn)
            return fn
        return decorator

    def context(self, fn):
        """Inject live data into every conversation turn.

        @app.context
        def my_data():
            "Current sales dataframe."
            return df.to_dict()
        """
        self._context_fn = fn
        return fn

    def on(self, event: str):
        """Register an event handler.

        @app.on("button_click")
        def handle_click(data: dict):
            key = data["key"]
            app.session[key] = True
            ...
        """
        def decorator(fn):
            self._on_handlers.setdefault(event, []).append(fn)
            return fn
        return decorator

    # ── Runtime system prompt ─────────────────────────────────────────

    def _effective_system(self) -> str:
        parts = [self.system_prompt]

        if self._context_fn:
            try:
                data  = self._context_fn()
                label = (self._context_fn.__doc__ or self._context_fn.__name__).strip().split("\n")[0]
                parts.append(f"\n\n--- Live Context: {label} ---\n{json.dumps(data, default=str)}")
            except Exception as e:
                parts.append(f"\n\n[Context error: {e}]")

        if self._components.has_any():
            names = ", ".join(f'"{n}"' for n in self._components.names())
            parts.append(
                f"\n\nWhen you want to render a visual component, reply with ONLY a JSON object "
                f"in this exact format: {{\"component\": <name>, \"data\": {{...}}}} "
                f"where <name> is one of: {names}. "
                "Do not include any other text — just the JSON."
            )

        return "".join(parts)

    # ── Component detection ───────────────────────────────────────────

    def _check_component(self, text: str) -> tuple[str, str] | None:
        stripped = text.strip()
        if not stripped.startswith("{"):
            return None
        try:
            obj  = json.loads(stripped)
            name = obj.get("component")
            if name and self._components.has(name):
                html = self._components.render(name, obj.get("data", obj))
                return name, html
        except (json.JSONDecodeError, Exception):
            pass
        return None

    # ── FastAPI app ───────────────────────────────────────────────────

    def _build_fastapi(self) -> FastAPI:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info(f"ChatUI starting — {self.provider}/{self.model} on :{self.port}")
            yield
            logger.info("ChatUI shutting down")

        fast = FastAPI(title=self.title, lifespan=lifespan)

        # CORS
        if self.cors_origins:
            fast.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Auth middleware
        if self.auth_key:
            @fast.middleware("http")
            async def auth_middleware(request: Request, call_next):
                if request.url.path in ("/", "/health", "/favicon.ico"):
                    return await call_next(request)
                auth = request.headers.get("Authorization", "")
                if auth != f"Bearer {self.auth_key}":
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                return await call_next(request)

        # Rate limit middleware
        if self._rate_limiter:
            @fast.middleware("http")
            async def rate_limit_middleware(request: Request, call_next):
                if request.url.path == "/ws":
                    return await call_next(request)
                client = request.client.host if request.client else "unknown"
                if not self._rate_limiter.check(client):
                    logger.warning(f"Rate limit hit for {client}")
                    return JSONResponse(
                        {"detail": "Too many requests. Slow down."}, status_code=429
                    )
                return await call_next(request)

        # Request logging
        @fast.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start = time.time()
            response = await call_next(request)
            duration = time.time() - start
            logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
            return response

        @fast.get("/")
        async def root():
            import json as _json
            html = UI_PATH.read_text(encoding="utf-8")
            html = html.replace("{{TITLE}}",         self.title)
            html = html.replace("{{LOGO}}",          self.logo)
            html = html.replace("{{SUBTITLE}}",      self.subtitle)
            html = html.replace("{{WELCOME_TITLE}}", self.welcome_title)
            html = html.replace("{{ACTIVE_THEME}}",  self.theme)
            html = html.replace("'{{CHIPS_JSON}}'",  _json.dumps(self.chips or []))
            html = html.replace("'{{THEMES_JSON}}'",  get_themes_json())
            html = html.replace("/*{{THEME_VARS}}*/",  get_css_vars(self.theme))
            return HTMLResponse(content=html)

        @fast.get("/health")
        async def health():
            return {
                "status": "ok",
                "version": "0.0.1",
                "provider": self.provider,
                "model": self.model,
                "tools": len(self._registry._tools),
                "components": len(self._components._renderers),
            }

        @fast.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket):
            auth_header = websocket.headers.get("authorization", "")
            if self.auth_key and auth_header != f"Bearer {self.auth_key}":
                await websocket.close(code=4001, reason="Unauthorized")
                return
            await self._handle_ws(websocket)

        return fast

    # ── Agentic loop — Anthropic ──────────────────────────────────────

    async def _loop_anthropic(self, history: list, send, stop: list) -> None:
        total_in = total_out = 0

        while True:
            if stop[0]:
                await send({"type": "stopped"}); return

            kwargs = {
                "model":      self.model,
                "max_tokens": 4096,
                "system":     self._effective_system(),
                "messages":   history,
            }
            if self._registry.has_tools():
                kwargs["tools"] = self._registry.get_schemas()

            full_text   = ""
            stop_reason = "end_turn"
            tool_uses   = []

            try:
                with self._client.messages.stream(**kwargs) as stream:
                    for event in stream:
                        if stop[0]: break
                        if (hasattr(event, "type")
                                and event.type == "content_block_delta"
                                and hasattr(event.delta, "text")):
                            chunk = event.delta.text
                            full_text += chunk
                            await send({"type": "token", "content": chunk})
                            await asyncio.sleep(0)

                    final      = stream.get_final_message()
                    stop_reason = final.stop_reason
                    total_in  += final.usage.input_tokens
                    total_out += final.usage.output_tokens

                    for block in final.content:
                        if block.type == "tool_use":
                            tool_uses.append(block)

            except Exception as e:
                logger.error(f"Anthropic stream error: {e}")
                await send({"type": "error", "content": str(e)}); return

            if stop[0]:
                await send({"type": "stopped"}); return

            # Component check
            if self._components.has_any() and full_text.strip():
                result = self._check_component(full_text)
                if result:
                    name, html = result
                    await send({"type": "component", "name": name, "html": html})

            # Append to history
            if full_text or tool_uses:
                content = []
                if full_text:
                    content.append({"type": "text", "text": full_text})
                for tu in tool_uses:
                    content.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
                history.append({"role": "assistant", "content": content})

            if stop_reason != "tool_use" or not tool_uses:
                await send({"type": "end", "usage": {"input": total_in, "output": total_out}})
                return

            # Execute tools
            tool_results = []
            for tu in tool_uses:
                await send({"type": "tool_call", "id": tu.id, "name": tu.name, "inputs": tu.input})
                try:
                    res     = self._registry.execute(tu.name, tu.input)
                except Exception as e:
                    res     = {"error": str(e)}
                    logger.error(f"Tool '{tu.name}' failed: {e}")
                res_str = self._registry.to_json(res)
                # If tool returned widgets, send them
                if isinstance(res, tuple) and all(isinstance(w, Widget) for w in res):
                    await send({"type": "widgets", "widgets": [w.to_payload() for w in res]})
                await send({"type": "tool_result", "id": tu.id, "name": tu.name, "result": res_str})
                tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": res_str})

            history.append({"role": "user", "content": tool_results})
            await send({"type": "start_again"})

    # ── Agentic loop — OpenAI-compatible (Ollama, Groq, OpenAI) ──────

    async def _loop_openai(self, history: list, send, stop: list) -> None:
        total_in = total_out = 0

        while True:
            if stop[0]:
                await send({"type": "stopped"}); return

            system   = self._effective_system()
            messages = [{"role": "system", "content": system}] + history

            kwargs: dict = {"model": self.model, "messages": messages, "stream": True}
            if self._registry.has_tools():
                kwargs["tools"]       = self._registry.get_openai_schemas()
                kwargs["tool_choice"] = "auto"

            full_text      = ""
            tc_raw: dict   = {}
            finish_reason  = "stop"

            try:
                stream = self._client.chat.completions.create(**kwargs)
                for chunk in stream:
                    if stop[0]: break

                    if hasattr(chunk, "usage") and chunk.usage:
                        total_in  = getattr(chunk.usage, "prompt_tokens",     0) or total_in
                        total_out = getattr(chunk.usage, "completion_tokens",  0) or total_out

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    delta  = choice.delta

                    if delta.content:
                        full_text += delta.content
                        await send({"type": "token", "content": delta.content})
                        await asyncio.sleep(0)

                    if delta.tool_calls:
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
                        "Cannot connect to Ollama. Make sure it is running.\n"
                        "Start it with:  ollama serve\n"
                        "Pull a model:   ollama pull llama3"
                    )
                logger.error(f"OpenAI stream error: {e}")
                await send({"type": "error", "content": msg}); return

            if stop[0]:
                await send({"type": "stopped"}); return

            tool_uses: list[_ToolCall] = []
            for idx in sorted(tc_raw):
                raw = tc_raw[idx]
                try:
                    input_data = json.loads(raw["arguments"] or "{}")
                except json.JSONDecodeError:
                    input_data = {}
                tool_uses.append(_ToolCall(
                    id    = raw["id"] or f"call_{idx}",
                    name  = raw["name"],
                    input = input_data,
                ))

            stop_reason = "tool_use" if (finish_reason == "tool_calls" and tool_uses) else "end_turn"

            if self._components.has_any() and full_text.strip():
                result = self._check_component(full_text)
                if result:
                    name, html = result
                    await send({"type": "component", "name": name, "html": html})

            if full_text or tool_uses:
                asst: dict = {"role": "assistant", "content": full_text or None}
                if tool_uses:
                    asst["tool_calls"] = [
                        {
                            "id":       tu.id,
                            "type":     "function",
                            "function": {"name": tu.name, "arguments": json.dumps(tu.input)},
                        }
                        for tu in tool_uses
                    ]
                history.append(asst)

            if stop_reason != "tool_use" or not tool_uses:
                await send({"type": "end", "usage": {"input": total_in, "output": total_out}})
                return

            for tu in tool_uses:
                await send({"type": "tool_call", "id": tu.id, "name": tu.name, "inputs": tu.input})
                try:
                    res     = self._registry.execute(tu.name, tu.input)
                except Exception as e:
                    res     = {"error": str(e)}
                    logger.error(f"Tool '{tu.name}' failed: {e}")
                res_str = self._registry.to_json(res)
                if isinstance(res, tuple) and all(isinstance(w, Widget) for w in res):
                    await send({"type": "widgets", "widgets": [w.to_payload() for w in res]})
                await send({"type": "tool_result", "id": tu.id, "name": tu.name, "result": res_str})
                history.append({"role": "tool", "tool_call_id": tu.id, "content": res_str})

            await send({"type": "start_again"})

    # ── Dispatch ──────────────────────────────────────────────────────

    async def _agentic_loop(self, history: list, send, stop: list) -> None:
        if self.provider == "anthropic":
            await self._loop_anthropic(history, send, stop)
        else:
            await self._loop_openai(history, send, stop)

    # ── WebSocket handler ─────────────────────────────────────────────

    async def _handle_ws(self, websocket: WebSocket):
        await websocket.accept()
        history: list = []
        stop    = [False]
        session = SessionState()

        async def send(payload: dict):
            await websocket.send_text(json.dumps(payload, default=str))

        await send({
            "type":     "config",
            "provider": self.provider,
            "model":    self.model,
            "session":  session.id,
        })

        if self._registry.has_tools():
            tools_info = [
                {"name": s["name"], "description": s.get("description", "")}
                for s in self._registry.get_schemas()
            ]
            await send({"type": "tools_ready", "tools": tools_info})

        if self._components.has_any():
            await send({"type": "components_ready", "components": self._components.names()})

        await send({"type": "session_state", "data": session.to_dict()})

        try:
            while True:
                raw     = await websocket.receive_text()
                payload = json.loads(raw)
                action  = payload.get("action")

                if action == "clear":
                    history = []
                    await send({"type": "cleared"})
                    continue

                if action == "stop":
                    stop[0] = True
                    continue

                if action == "update_system":
                    self.system_prompt = payload.get("prompt", self.system_prompt)
                    await send({"type": "system_updated"})
                    continue

                if action == "set_session":
                    key = payload.get("key")
                    val = payload.get("value")
                    if key is not None:
                        session[key] = val
                        await send({"type": "session_updated", "key": key, "value": val})
                    continue

                if action == "get_session":
                    await send({"type": "session_state", "data": session.to_dict()})
                    continue

                if action == "widget_event":
                    event_type = payload.get("event", "")
                    widget_id  = payload.get("widget_id", "")
                    widget_key = payload.get("key", "")
                    value      = payload.get("value")
                    data       = payload.get("data", {})

                    if event_type == "button_click" and widget_key in self._on_handlers:
                        for handler in self._on_handlers.get(widget_key, []):
                            try:
                                result = handler(data or {"key": widget_key})
                                if isinstance(result, (str, dict, list)):
                                    await send({"type": "token", "content": json.dumps(result, default=str)})
                                    await send({"type": "end", "usage": {"input": 0, "output": 0}})
                            except Exception as e:
                                await send({"type": "error", "content": str(e)})

                    for handler in self._on_handlers.get(f"__{event_type}__", []):
                        try:
                            handler(data or {"widget_id": widget_id, "key": widget_key, "value": value})
                        except Exception as e:
                            logger.error(f"Event handler error: {e}")

                    continue

                if action == "regenerate":
                    while history:
                        last = history[-1]
                        if last["role"] == "user" and isinstance(last.get("content"), str):
                            break
                        history.pop()
                    if not history:
                        continue
                    stop[0] = False
                    if not self._client:
                        await send({"type": "start"})
                        await send({"type": "error", "content": _no_key_msg(self.provider)})
                        continue
                    await send({"type": "start"})
                    await self._agentic_loop(history, send, stop)
                    continue

                user_msg = payload.get("message", "").strip()
                if not user_msg:
                    continue

                stop[0] = False
                history.append({"role": "user", "content": user_msg})
                if len(history) > 40:
                    history = history[-40:]

                if not self._client:
                    await send({"type": "start"})
                    await send({"type": "error", "content": _no_key_msg(self.provider)})
                    continue

                await send({"type": "start"})
                await self._agentic_loop(history, send, stop)

        except WebSocketDisconnect:
            pass
        except Exception as err:
            logger.exception(f"WebSocket error: {err}")
            try:
                await send({"type": "error", "content": str(err)})
            except Exception:
                pass

    # ── Run ───────────────────────────────────────────────────────────

    def run(self, host: str = None, port: int = None, **kwargs):
        """Start the ChatUI server."""
        h = host or self.host
        p = port or self.port

        if self.open_browser:
            import threading, webbrowser
            def _open():
                import time
                time.sleep(1.0)
                webbrowser.open(f"http://localhost:{p}")
            threading.Thread(target=_open, daemon=True).start()

        tool_count = len(self._registry._tools)
        comp_count = len(self._components._renderers)

        print(f"\n  ChatUI v0.0.1  |  {self.provider} / {self.model}  |  {self.theme} theme")
        print(f"  Running at   http://localhost:{p}")
        print(f"  Health check http://localhost:{p}/health")
        if self.auth_key:
            print(f"  Auth          enabled (Bearer token)")
        if self._rate_limiter:
            print(f"  Rate limit    {self._rate_limiter._max} req/min")
        if tool_count:
            print(f"  Tools         {tool_count}: {', '.join(self._registry._tools)}")
        if comp_count:
            print(f"  Components    {comp_count}: {', '.join(self._components._renderers)}")
        if self._context_fn:
            print(f"  Context       {self._context_fn.__name__}()")
        if self._on_handlers:
            for evt, handlers in self._on_handlers.items():
                names = ", ".join(h.__name__ for h in handlers)
                print(f"  On[{evt}]      {names}")
        print()

        uvicorn.run(self.app, host=h, port=p, log_level="warning", **kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _no_key_msg(provider: str) -> str:
    env = _ENV_KEYS.get(provider)
    if provider == "ollama":
        return (
            "Ollama is not configured. Install it and start it:\n"
            "  brew install ollama\n"
            "  ollama pull llama3\n"
            "  ollama serve"
        )
    return (
        f"No API key for provider '{provider}'. "
        f"Pass api_key='...' to ChatUI() or set the {env} environment variable."
    )
