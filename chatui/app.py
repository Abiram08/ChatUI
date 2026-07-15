"""
chatui/app.py
ChatUI — main application class.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional

from ._constants import (
    DEFAULT_SYSTEM,
    MAX_HISTORY_TURNS,
    VERSION,
    _ENV_KEYS,
    _PROVIDERS,
    _check_api_key,
    _no_key_msg,
)
from ._rate_limiter import _RateLimiter
from .exceptions import ChatUIRegistrationError
from .runtime.connection import ConnectionState
from .runtime.history import truncate_history
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

logger = logging.getLogger("chatui")


class ChatUI:
    """
    Production chat UI for Python AI apps.

    Quickstart::

        from chatui import chat
        chat()

    With tools::

        from chatui import chat

        def get_weather(city: str) -> dict:
            \"\"\"Current weather for a city.\"\"\"
            return {"city": city, "temp": "22C"}

        chat(tools=[get_weather], title="Weather Bot")

    Advanced (decorators)::

        app = ChatUI(provider="groq")

        @app.tool
        def get_weather(city: str) -> dict:
            \"\"\"Current weather for a city.\"\"\"
            return {"city": city, "temp": "22C"}

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
        system_prompt: str | None = None,
        title: str = "ChatUI",
        logo: str = "\u25c6",
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
        tools: list | None = None,
        components: dict | None = None,
        on: dict | None = None,
        reply: Callable | None = None,
        history_turns: int | None = None,
        allow_client_system_prompt: bool = False,
        themes: list[str] | None = None,
        lite: bool = False,
    ):
        from .providers.detect import detect_provider_from_env

        if provider == "auto" and reply is None:
            provider, default_model = detect_provider_from_env()
            if model is None:
                model = default_model
        elif provider == "auto" and reply is not None:
            provider = "echo"

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
        self.allow_client_system_prompt = allow_client_system_prompt
        self.history_turns = history_turns or MAX_HISTORY_TURNS
        self._reply_fn = reply
        self._themes_subset = themes
        self.lite = lite

        self._registry = ToolRegistry()
        self._components = ComponentRegistry()
        self._context_fn: Optional[Callable] = None
        self._on_handlers: dict[str, list[Callable]] = {}
        self._hooks: dict[str, list[Callable]] = {}
        self._rate_limiter = (
            _RateLimiter(max_requests=rate_limit) if rate_limit and rate_limit > 0 else None
        )
        self._fallback_session = SessionState()

        is_prod = os.environ.get("CHATUI_ENV") == "production"
        if is_prod and self.cors_origins == ["*"]:
            logger.warning(
                "CORS is set to ['*'] in production. "
                "Set cors_origins=['https://yourdomain.com'] for security."
            )
        if is_prod and not lite:
            logger.info("CHATUI_ENV=production: consider setting lite=True")

        logging.basicConfig(
            level=getattr(logging, (log_level or "info").upper(), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        if tools:
            self.add_tools(*tools)
        if components:
            self.add_components(components)
        if on:
            self.add_handlers(on)

        default_model, base_url = _PROVIDERS[p]
        self.model = model or default_model
        self._base_url = base_url

        if self._reply_fn is not None:
            self._provider = None
            self._client = None
        else:
            self._client = self._build_client(p, api_key, base_url)
            self._provider = self._build_provider(p, self._client)

    @property
    def session(self) -> SessionState:
        current = get_current_session()
        return current if current is not None else self._fallback_session

    def _build_client(self, provider: str, api_key: str | None, base_url: str | None):
        if provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise ImportError(
                    "Install anthropic: pip install 'chatui[anthropic]'"
                ) from e
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            return AsyncAnthropic(api_key=key) if key else None

        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                f"Provider '{provider}' needs the openai package: pip install 'chatui[{provider}]'"
            ) from e

        if provider == "ollama":
            return AsyncOpenAI(api_key="ollama", base_url=base_url)

        key = api_key or os.getenv(_ENV_KEYS.get(provider) or "")
        if not key:
            return None
        if provider == "groq":
            return AsyncOpenAI(api_key=key, base_url=base_url)
        return AsyncOpenAI(api_key=key)

    def _build_provider(self, provider_name: str, client):
        if client is None:
            return None
        if provider_name == "anthropic":
            from .providers.anthropic import AnthropicProvider
            return AnthropicProvider(client=client, model=self.model)
        else:
            from .providers.openai_compat import OpenAICompatProvider
            return OpenAICompatProvider(client=client, model=self.model, provider_name=provider_name)

    def register_tool(self, fn: Callable, name: str | None = None) -> Callable:
        if name:
            fn.__name__ = name
        if fn.__name__ in self._registry.names():
            raise ChatUIRegistrationError("Tool", fn.__name__)
        self._registry.register(fn)
        return fn

    def register_component(self, name: str, fn: Callable) -> None:
        if name in self._components.names():
            raise ChatUIRegistrationError("Component", name)
        self._components.register(name, fn)

    def register_handler(self, event: str, fn: Callable) -> None:
        self._on_handlers.setdefault(event, []).append(fn)

    def add_tools(self, *fns) -> ChatUI:
        for fn in fns:
            if isinstance(fn, list):
                for f in fn:
                    self.register_tool(f)
            elif isinstance(fn, dict):
                for name, f in fn.items():
                    self.register_tool(f, name=name)
            else:
                self.register_tool(fn)
        return self

    def add_components(self, components: dict) -> ChatUI:
        for name, fn in components.items():
            self.register_component(name, fn)
        return self

    def add_handlers(self, handlers: dict) -> ChatUI:
        for event, fn in handlers.items():
            self.register_handler(event, fn)
        return self

    def on_token(self, fn: Callable) -> Callable:
        self._hooks.setdefault("on_token", []).append(fn)
        return fn

    def on_tool(self, fn: Callable) -> Callable:
        self._hooks.setdefault("on_tool", []).append(fn)
        return fn

    def on_error(self, fn: Callable) -> Callable:
        self._hooks.setdefault("on_error", []).append(fn)
        return fn

    def on_end(self, fn: Callable) -> Callable:
        self._hooks.setdefault("on_end", []).append(fn)
        return fn

    async def _run_hooks(self, event: str, *args) -> None:
        for fn in self._hooks.get(event, []):
            try:
                result = fn(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.debug("Hook %s failed", event, exc_info=True)

    def tool(self, fn: Callable = None, *, name: str | None = None):
        def deco(f: Callable) -> Callable:
            return self.register_tool(f, name=name)
        return deco(fn) if fn is not None else deco

    def component(self, name: str):
        def deco(fn: Callable) -> Callable:
            self.register_component(name, fn)
            return fn
        return deco

    def context(self, fn: Callable = None):
        def deco(f: Callable) -> Callable:
            self._context_fn = f
            return f
        return deco(fn) if fn is not None else deco

    def on(self, event: str):
        def deco(fn: Callable) -> Callable:
            self.register_handler(event, fn)
            return fn
        return deco

    async def _effective_system(self, conn: ConnectionState) -> str:
        parts = [conn.system_prompt]

        if self._context_fn:
            try:
                if asyncio.iscoroutinefunction(self._context_fn):
                    data = await self._context_fn(conn.session)
                else:
                    data = await asyncio.to_thread(self._context_fn, conn.session)
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
        import re

        stripped = (text or "").strip()

        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict) and "component" in obj:
                    name = obj.get("component")
                    if name and self._components.has(name):
                        html = self._components.render(name, obj.get("data", {}))
                        return name, html
            except (json.JSONDecodeError, TypeError):
                pass

        match = re.search(r'```(?:json)?\s*(\{.*?"component".*?\})\s*```', stripped, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(1))
                if isinstance(obj, dict):
                    name = obj.get("component")
                    if name and self._components.has(name):
                        html = self._components.render(name, obj.get("data", {}))
                        return name, html
            except (json.JSONDecodeError, TypeError):
                pass

        if "component" in stripped:
            match = re.search(r'\{[^{}]*"component"[^{}]*\}', stripped, re.DOTALL)
            if match:
                try:
                    obj = json.loads(match.group(0))
                    if isinstance(obj, dict):
                        name = obj.get("component")
                        if name and self._components.has(name):
                            html = self._components.render(name, obj.get("data", {}))
                            return name, html
                except (json.JSONDecodeError, TypeError):
                    pass

        return None

    async def _run_tool(self, name: str, inputs: dict) -> Any:
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
        widgets = collect_widgets(result)
        if widgets:
            await send({"type": "widgets", "widgets": widget_payloads(widgets)})
        clean = strip_widgets(result)
        return self._registry.to_json(clean)

    async def _emit_handler_result(self, send: Callable, result: Any) -> None:
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

    def _authorized(self, authorization: str = "", token: str = "") -> bool:
        if not self.auth_key:
            return True
        if authorization == f"Bearer {self.auth_key}":
            return True
        if token and token == self.auth_key:
            return True
        return False

    # Server-lifetime methods (build, run, etc.)

    def build_app(self):
        """Build and return the FastAPI app for this ChatUI instance."""
        from .server.builder import build_fastapi_app
        return build_fastapi_app(self)

    def run(self, host: str = None, port: int = None, **kwargs):
        """Start the ChatUI server (blocking)."""
        from dotenv import load_dotenv

        load_dotenv()

        h = host or self.host
        p = port or self.port

        if os.environ.get("CHATUI_ENV") == "production":
            self.open_browser = False

        if self.open_browser:
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
            print("  Auth          enabled (Bearer header / ?token=)")
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
        if self._reply_fn:
            print(f"  Reply         {self._reply_fn.__name__}()  (no LLM)")
        if self._provider is None and self._reply_fn is None and self.provider != "ollama":
            from ._constants import _ENV_KEYS
            print(f"  Warning       no API key — set {_ENV_KEYS.get(self.provider)}")
        print()

        import uvicorn
        uvicorn.run(self.app, host=h, port=p, log_level="warning", **kwargs)

    @classmethod
    def from_env(cls, **kwargs) -> ChatUI:
        from .providers.detect import detect_provider_from_env

        provider, model = detect_provider_from_env()
        kwargs.setdefault("provider", provider)
        kwargs.setdefault("model", model)
        return cls(**kwargs)

    def asgi(self):
        """Return the FastAPI app for embedding in another ASGI server."""
        return self.app

    def mount(self, parent_app, path: str = "/chat") -> None:
        """Mount ChatUI into an existing FastAPI app."""
        parent_app.mount(path, self.app)

    @property
    def app(self):
        if not hasattr(self, "_app"):
            self._app = self.build_app()
        return self._app

    @app.setter
    def app(self, value):
        self._app = value
