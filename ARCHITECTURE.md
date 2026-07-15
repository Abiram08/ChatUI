# ChatUI — Architecture & Source Guide

> **Audience**: contributors, maintainers, and AI assistants working on this **open-source** library.  
> **Goal**: understand the whole system — data flows, modules, UI assembly, and extension points — so changes stay coherent.

**ChatUI** is a MIT-licensed, single-Python-process framework for production LLM chat UIs.  
It competes with “Streamlit for chatbots”: developer writes Python; users get a premium streaming chat interface with tools, widgets, and themes — **no Node.js, no frontend build**.

**Core promise**

```python
from chatui import chat
chat(provider="groq")
```

→ professional browser UI with real-time streaming and tool calling.

Related docs:

| Doc | Role |
|-----|------|
| [README.md](README.md) | Install, API, demos, contributing |
| [AGENTS.md](AGENTS.md) | Brand + design law for UI work |
| [LICENSE](LICENSE) | MIT |

---

## 1. High-level architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                            │
│  • index.html shell + client JS                                     │
│  • CSS assembled server-side (modular partials, zero Node)           │
│  • Vendored JS (marked / DOMPurify / highlight.js) — no CDN          │
│  • WebSocket → /ws                                                   │
│  • Streaming markdown, tool cards, widgets, components              │
│  • localStorage conversations · live theme/font/size                │
└─────────────────────────────────────────────────────────────────────┘
                                ↕ JSON over WebSocket (protocol_version: 1)
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI + Uvicorn  (chatui/server.py)                              │
│  • GET /  → render_html(theme_vars) + template fills                │
│  • GET /health · GET /vendor/* · GET /js/*  (StaticFiles)           │
│  • WS /ws · auth · rate limit · logging                             │
│  • ConnectionState per WebSocket (runtime/connection.py)             │
│  • Unified agent loop (agent/loop.py) driven by Provider Protocol   │
│  • Provider adapters (providers/) → unified Events                  │
│  • Tool run off event loop · widget side-effects · components        │
└─────────────────────────────────────────────────────────────────────┘
                                ↕
┌─────────────────────────────────────────────────────────────────────┐
│  LLM providers  (chatui/providers/)                                 │
│  anthropic | openai_compat (groq · ollama · openai) | detect         │
└─────────────────────────────────────────────────────────────────────┘
```

Everything runs in **one Python process**. Frontend assets ship inside the wheel; CSS is concatenated at request time; vendored JS libs are served locally from `/vendor`.

---

## 2. Project structure (current)

```
ChatUI/
├── AGENTS.md                 # Design principles (do not violate for UI)
├── ARCHITECTURE.md           # This file
├── README.md
├── LICENSE                   # MIT — open source
├── pyproject.toml            # package metadata, extras, pytest, hatch
├── requirements.txt
├── .github/workflows/ci.yml  # pytest on Python 3.9 / 3.11 / 3.12
│
├── chatui/
│   ├── __init__.py           # Public API + CLI entrypoint + chat() shim
│   ├── api.py                # chat() facade + from_env() (beginner API)
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── server.py             # ChatUI class, FastAPI, WS, embedding hooks
│   ├── tools.py              # ToolRegistry + ComponentRegistry
│   ├── widgets.py            # Widget + builders + collect/strip
│   ├── session.py            # SessionState + contextvar helpers
│   ├── themes.py             # OKLCH theme factory (9 palettes)
│   │
│   ├── providers/            # LLM provider adapters + detection
│   │   ├── __init__.py        # Re-exports Protocol + Events + detect
│   │   ├── base.py            # Provider Protocol + Event dataclasses
│   │   ├── anthropic.py       # Anthropic adapter (native tool_use)
│   │   ├── openai_compat.py   # OpenAI-compatible adapter (groq/ollama/openai)
│   │   └── detect.py          # detect_provider_from_env()
│   │
│   ├── agent/                # Unified agent loop
│   │   ├── __init__.py
│   │   └── loop.py            # agent_loop() — shared tool-round logic
│   │
│   ├── runtime/              # Per-connection runtime helpers
│   │   ├── __init__.py
│   │   ├── connection.py     # ConnectionState dataclass
│   │   └── history.py         # truncate_history / repair_tool_pairs
│   │
│   └── ui/
│       ├── __init__.py
│       ├── assets.py          # load_css / render_html (no build step)
│       ├── index.html         # Shell + JS; /*{{STYLES}}*/ placeholder
│       ├── css/
│       │   ├── manifest.txt   # Partial order
│       │   ├── 00-tokens.css
│       │   ├── 01-shell.css
│       │   ├── 02-main.css
│       │   ├── 03-messages.css
│       │   ├── 04-tools.css
│       │   ├── 05-widgets.css
│       │   ├── 06-composer.css
│       │   └── 07-responsive.css
│       ├── js/               # Optional split JS (served from /js)
│       └── vendor/           # Vendored libs — served from /vendor, no CDN
│           ├── marked.min.js
│           ├── purify.min.js
│           ├── highlight.min.js
│           └── github-dark.min.css
│
├── tests/                    # Unit + HTTP + WS smoke tests
│   ├── test_widgets.py
│   ├── test_layout.py
│   ├── test_themes.py
│   ├── test_session.py
│   ├── test_tools.py
│   ├── test_tool_schemas.py
│   ├── test_assets.py
│   ├── test_server.py
│   ├── test_ws.py
│   ├── test_runtime.py
│   ├── test_registration.py
│   ├── test_api.py
│   └── test_public_api.py
│
├── demo/
│   ├── demo_groq.py          # Minimal starter
│   ├── demo_beginner.py      # Beginner chat() API
│   ├── demo_echo.py          # Custom reply (no LLM key)
│   └── demo_full.py          # Tools, components, widgets, events
│
└── scripts/
    └── split_css.py          # Maintainer helper to re-split CSS
```

**Key insight**: the library stays small and layered. The `providers/` package gives a uniform `Provider` Protocol (yields `Event`s); `agent/loop.py` consumes those Events and runs the tool rounds once for all providers; `runtime/` owns per-connection state and history repair; `api.py` is the beginner-facing facade. `server.py` glues FastAPI + WS + embedding; the frontend is modular CSS + one HTML shell + vendored JS.

---

## 3. Python modules

### 3.1 `chatui/__init__.py`

Public surface for open-source consumers:

- `ChatUI`, `SessionState`, `VERSION`, `Widget`
- `chat()` facade (re-exported from `api.py`)
- All widget builders (`button`, `metric`, …)
- CLI: `python -m` / `chatui` → `main()`

### 3.2 `chatui/api.py`

Beginner-facing facade — the simplest way to start a chatbot:

```python
from chatui import chat
chat(tools=[get_weather], title="Weather Bot")
```

- `chat(**kwargs)` builds a `ChatUI` and calls `.run()` in one call
- Accepts plain-function `tools`, `components`, `on` (event handlers) — no decorators required
- Supports `reply` (sync/async/async-gen) for LLM-free bots
- `provider="auto"` → `detect_provider_from_env()`

### 3.3 `chatui/exceptions.py`

Custom exception hierarchy for clear, copy-paste-friendly errors:

| Class | Meaning |
|-------|---------|
| `ChatUIError` | Base class |
| `ChatUINoProviderError` | No provider detected from env (prints platform-correct export hints) |
| `ChatUIMissingKeyError` | Provider requires an API key but none is set |
| `ChatUIOllamaError` | Cannot reach Ollama at `localhost:11434` |
| `ChatUIProviderError` | Provider-specific runtime error |
| `ChatUIRegistrationError` | Duplicate tool / component / handler name |

Errors include platform-aware (`$env:` on Windows, `export` elsewhere) setup hints.

### 3.4 `chatui/session.py`

```python
_current_session: ContextVar[Optional[SessionState]] = ContextVar(...)
```

**Why contextvars?**  
Tools and `@app.on` handlers may run in `asyncio.to_thread`. `app.session` must resolve to the **correct WebSocket connection** even from worker threads.

`SessionState`:

- Always truthy (`__bool__` → `True`) so `session or fallback` works
- Dict protocol: `[]`, `.get`, `.set`, `.update`, `.to_dict()`, `.reset()`
- Short `id` for debugging

Helpers: `get_current_session`, `set_current_session`, `reset_current_session`.

### 3.5 `chatui/providers/`

A small package that abstracts LLM streaming behind a uniform Protocol.

#### `base.py` — Provider Protocol + Event types

All adapters translate their native stream chunks into these dataclasses:

| Event | Carries |
|-------|---------|
| `TokenEvent` | `text` delta |
| `ToolCallEvent` | `id`, `name`, `input` |
| `ToolResultEvent` | `id`, `name`, `result` |
| `EndEvent` | `stop_reason`, `input_tokens`, `output_tokens` |
| `ErrorEvent` | `message` |

`Provider` is a `@runtime_checkable` `Protocol` with one method:

```python
async def stream(self, messages, tools, system, stop_event) -> AsyncIterator[Event]
```

The agent loop works with **any** `Provider` — it never imports provider-specific shapes.

#### `anthropic.py`

Adapter for `AsyncAnthropic` — native `tool_use` blocks, Anthropic-style tool_result batching, `append_assistant` / `append_tool_result` helpers.

#### `openai_compat.py`

Shared adapter for OpenAI-shaped APIs: `openai`, `groq` (via `base_url`), `ollama` (via `base_url`). Translates `tool_calls`-by-index into the same Events.

#### `detect.py`

`detect_provider_from_env()` → `(provider, default_model)` by checking `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (priority order), then probing Ollama at `localhost:11434`. Raises `ChatUINoProviderError` when none found.

### 3.6 `chatui/agent/loop.py`

Unified agent loop — `agent_loop(provider, conn, send, *, registry, components, ...)`:

- Consumes `Event`s from any `Provider` via `provider.stream(...)`
- Streams `token` messages to the client
- Executes tool calls (off the event loop via `asyncio.to_thread`, with session rebinding)
- Emits widget side-effects (`collect_widgets` → `widgets` message; `strip_widgets` → model)
- Detects component requests in the model output (exact JSON / fenced / prose)
- Honors `conn.stop_event` for cancellation
- Enforces `MAX_TOOL_ROUNDS = 12`
- Calls back to provider-specific `append_assistant` / `append_tool_result` to keep history in the right shape

This replaces the previous duplicated `_loop_anthropic` / `_loop_openai` functions in `server.py`.

### 3.7 `chatui/runtime/`

#### `connection.py` — `ConnectionState`

Per-WebSocket state, fixing the multi-user footgun where one client could mutate shared app-level state:

```python
@dataclass
class ConnectionState:
    session: SessionState        # per-user state dict
    history: list                 # this conversation's messages
    system_prompt: str            # per-connection copy of app default
    stop_event: asyncio.Event     # cancellation
    generating: bool
    user_id: Optional[str]
```

- `system_prompt` is a **per-connection copy** — clients editing it (when `allow_client_system_prompt=True`) only affect their own socket
- Helpers: `request_stop()` / `reset_stop()` / `clear_history()` / `pop_to_last_user_message()` (for regenerate)

#### `history.py`

- `truncate_history(history, max_turns=40)` — trims at user→assistant turn boundaries; never cuts mid tool-call pair
- `repair_tool_pairs(history)` — drops orphaned `tool_result` (Anthropic) or `tool_calls` (OpenAI) at the boundary so the API never sees a dangling pair

### 3.8 `chatui/tools.py`

#### ToolRegistry

- Reads docstring (first line = model description), signature, type hints
- Builds Anthropic `input_schema` and OpenAI `function.parameters`
- `execute(name, inputs)` **never raises** to the model → `{"error": ...}`
- `get_schemas()` / `get_openai_schemas()` for provider-specific tool formats

**Known limitation (open for contributions):** schemas are basic (no per-param descriptions, enums, or constraints). Optional Pydantic integration is a natural extension.

#### ComponentRegistry

When the model emits **exactly**:

```json
{"component": "dashboard", "data": {...}}
```

the registered Python renderer returns an HTML string injected as a component card.

### 3.9 `chatui/widgets.py`

- `Widget` — small container (`type`, `id`, `props`) + `to_payload()`
- Builders return widgets; tools/handlers may return one widget, a sequence, or mix of widgets + data
- `collect_widgets` — recursive extract  
- `strip_widgets` — JSON-safe value for the model  
- `widget_payloads` — JSON-serializable shapes for the wire
- Pure widget returns become `{"ok": true, "ui": ["button", ...]}`

Layout intent (enforced in the frontend renderer):

| Pattern | UI result |
|---------|-----------|
| Consecutive `button`s | `.w-actions` row |
| Consecutive `metric`s | `.w-metrics` strip |
| `columns` … `end_columns` | CSS `fr` grid |
| `button` / `divider` / `spinner` alone | `.widget-card.flat` |

### 3.10 `chatui/themes.py`

Themes are built by a shared `_theme(mode, hue=…, accent_hue=…)` factory (DRY, clean-code).

- 5 light + 4 dark
- Tinted neutrals only (no pure `#000` / `#fff`)
- Tokens include `--accent-fg` for text *on* accent surfaces
- `get_css_vars(name)` → `:root { … }` for SSR injection  
- `get_themes_json(subset=None)` → client-side live switcher; passing a subset shrinks the payload when `ChatUI(themes=[...])` is used

| Name | Mode | Character |
|------|------|-----------|
| manuscript | light | Warm paper, terracotta |
| atoll | light | Cool salt, teal |
| grain | light | Beige, olive |
| rose | light | Blush |
| mint | light | Fresh green |
| ink | dark | Near-black, amber |
| obsidian | dark | Graphite, coral |
| nocturne | dark | Navy, soft periwinkle |
| midnight | dark | Charcoal slate, indigo |

### 3.11 `chatui/ui/assets.py`

Zero-build asset pipeline:

1. Read `css/manifest.txt`
2. Concatenate partials (with file banners for debugging)
3. Prepend theme vars
4. Replace `/*{{STYLES}}*/` in `index.html`

`load_css()` is cached (`lru_cache`); `clear_asset_cache()` exists for tests. Vendored JS/CSS in `ui/vendor/` and split JS in `ui/js/` are served by FastAPI `StaticFiles` (see §3.12).

### 3.12 `chatui/server.py` (core)

`ChatUI` is the central class. It owns the FastAPI app, registries, provider client, theme, optional auth/rate-limit, and the WebSocket handler.

#### Init

- Resolve provider + default model (or `"auto"` → `detect_provider_from_env()`)
- Build the provider adapter (`AsyncAnthropic` or `AsyncOpenAI` with `base_url` for groq/ollama)
- `ToolRegistry`, `ComponentRegistry`, event map, hook map
- FastAPI: `StaticFiles` mounts for `/vendor` and `/js`, CORS, optional auth middleware, optional rate limit, logging
- Routes: `GET /`, `GET /health`, `WebSocket /ws`

#### Per-connection WebSocket

1. Build a fresh `ConnectionState` (its own `SessionState`, `history`, `system_prompt` copy, `stop_event`)
2. Bind `SessionState` contextvar
3. Send `config` (includes `protocol_version: 1`, `version`, `provider`, `model`), `tools_ready`, `components_ready`, `session_state`
4. Dispatch: `chat` · `widget_event` · `regenerate` · `stop` · `clear` · `update_system` · session get/set

`update_system` writes only to `conn.system_prompt` (per-connection). When `allow_client_system_prompt=False`, client updates are rejected. The auth token is **never** written into the rendered HTML — the `{{AUTH_TOKEN}}` placeholder is replaced with `''` so the client uses header / `?token=` auth only.

#### Agent loop

On `chat` / `regenerate`, `server.py` invokes `agent_loop(provider, conn, send, ...)` (see §3.6). The loop runs the unified tool rounds, streaming `token` / `tool_call` / `tool_result` / `widgets` / `component` / `end` messages. History is truncated via `truncate_history()` before the request.

#### Hooks

Lifecycle hooks that fire during a turn — register with decorators:

```python
@app.on_token
async def _(text): ...           # each token/chunk

@app.on_tool
async def _(name, inputs): ...   # before each tool call

@app.on_error
async def _(message): ...        # on stream error

@app.on_end
async def _(usage): ...          # at turn end (usage = {input, output})
```

Hooks run on the same event loop as the agent loop (no thread rebinding for hooks themselves).

#### Embedding in another ASGI app

- `ChatUI.asgi()` → returns the underlying `FastAPI` app, so you can run it with any ASGI server (`uvicorn myapp:app`)
- `ChatUI.mount(parent_app, path="/chat")` → mounts ChatUI under a path on an existing FastAPI app

```python
from fastapi import FastAPI
from chatui import ChatUI

api = FastAPI()
chat = ChatUI(provider="groq")
chat.mount(api, "/chat")
```

#### Theme / lite options

- `themes=["manuscript", "ink"]` — restrict the client-side theme switcher to a subset; `get_themes_json(subset)` shrinks the inlined JSON payload
- `lite=True` — lightweight mode (reduces chrome/features for embedding); off by default

#### Safety limits

```python
MAX_MESSAGE_CHARS = 12_000
MAX_HISTORY_TURNS = 40
MAX_FILE_BYTES    = 2 * 1024 * 1024
MAX_TOOL_ROUNDS   = 12
```

---

## 4. Frontend

### 4.1 Delivery model

| Piece | Role |
|-------|------|
| `index.html` | Landmarks, composer, sidebar, JS app |
| `css/*` | Modular styles by concern |
| `vendor/*` | `marked.min.js`, `purify.min.js`, `highlight.min.js`, `github-dark.min.css` — vendored, served from `/vendor` |
| `js/*` | Optional split JS, served from `/js` |
| `assets.py` | Assemble CSS at serve time |

Still **no Node**, no Vite/Webpack, **and no CDN**. All JS libraries ship inside the wheel and are served locally by FastAPI `StaticFiles`, so ChatUI is fully offline-capable and free of third-party-host dependencies. Maintainability comes from partials + manifest, not a JS toolchain.

### 4.2 CSS partials (order)

1. `00-tokens` — spacing, radii, line-height, focus, skip-link, reduced-motion  
2. `01-shell` — app chrome, sidebar, settings  
3. `02-main` — welcome / main column  
4. `03-messages` — bubbles, prose, markdown  
5. `04-tools` — thinking, tool cards, components  
6. `05-widgets` — buttons, metrics, tables, layout  
7. `06-composer` — toasts, input, send/stop  
8. `07-responsive` — breakpoints, print, touch  

### 4.3 Accessibility (current baseline)

- Skip link → `#ci` (composer)  
- `:focus-visible` rings; high-contrast media query  
- Settings / sidebar `aria-expanded`; Escape closes panels  
- Status & expander heads are real `<button>`s  
- Message list: `role="log"` + `aria-live="polite"`  
- Connection banner: `role="alert"`  

### 4.4 Client state (`S`)

```js
{
  ws, connected, streaming,
  streamEl, raw, thinkId, tbEl, currentAiMsg,
  convs, msgHistory, aid,
  session: {},
  ascroll
}
```

### 4.5 WebSocket protocol

All server→client messages on the `/ws` socket are tagged with `protocol_version: 1` (sent in the initial `config` message). Client→server messages use an `action` field.

**Client → server**

| Action | Purpose |
|--------|---------|
| `chat` | User message |
| `widget_event` | Button, input, upload, etc. |
| `regenerate` | Redo last assistant turn |
| `stop` | Cancel generation |
| `clear` | Reset server history |
| `update_system` | New system prompt (per-connection; gated by `allow_client_system_prompt`) |
| `set_session` / `get_session` | Session bridge |

**Server → client**

| Type | Purpose |
|------|---------|
| `config` | Bootstrap — includes `protocol_version: 1`, `version`, `provider`, `model`, `session` |
| `tools_ready`, `components_ready`, `session_state` | Bootstrap |
| `start` / `start_again` | Stream begin / next tool round |
| `token` | Text delta |
| `tool_call` / `tool_result` | Tool card lifecycle |
| `widgets` | Interactive UI payloads |
| `component` | Named HTML card |
| `end` | Finish (+ usage when available) |
| `stopped`, `error`, `cleared`, … | Control / errors |

### 4.6 Widget rendering pipeline

```
widgets[] → renderWidgetGroup
              ├─ columns / expander containers
              ├─ toast → showToast
              ├─ button run → renderButtonGroup
              ├─ metric run → renderMetricGroup
              └─ else → renderWidget (+ flat shell when needed)
                    → buildWidgetHTML + bindWidgetEvents
```

### 4.7 Persistence

- Index: `localStorage` key `cui3`  
- Messages: `cui_msgs_<id>`  
- Loaded chats are view-only until a new message (server history is per-socket)

---

## 5. Example flow: tool + widgets

1. User: “Show widgets”  
2. Server appends user message → `agent_loop()`  
3. Model calls `show_widgets` → adapter yields `ToolCallEvent`  
4. UI shows tool card (running)  
5. Tool returns `(metric…, button…)`  
6. `collect_widgets` → `widgets` message to browser  
7. `strip_widgets` → model sees `{"ok": true, "ui": [...]}`  
8. Frontend groups metrics and buttons into proper layout  
9. User clicks button → `widget_event` → `@app.on` handler  

---

## 6. Demos vs production tools

`demo/demo_full.py` tools are **illustrative** (random weather, fake DB). They prove the **mechanism** (tools + widgets + components), not production data quality.

For a real open-source showcase, prefer:

- Real APIs (e.g. Open-Meteo)  
- Validated inputs  
- Stable, documented return shapes  
- Clear errors for the model and the user  

Contributions that replace mock tools with honest integrations are highly valued.

---

## 7. Testing & CI (open-source quality bar)

```bash
pip install -e ".[dev]"
pytest --cov=chatui
```

| File | Intent |
|------|--------|
| `test_widgets` | Builders, clamping, collect/strip |
| `test_layout` | Widget grouping / layout intent |
| `test_themes` | Token completeness, no pure black/white, export |
| `test_session` | Dict API + contextvar bind/reset |
| `test_tools` | Schema gen, execute errors, components |
| `test_tool_schemas` | Anthropic vs OpenAI schema shapes |
| `test_assets` | Manifest + CSS/HTML assembly |
| `test_server` | `/health`, `/` HTML, rate limiter, decorators |
| `test_ws` | WebSocket handshake + bootstrap messages |
| `test_runtime` | `truncate_history` / `repair_tool_pairs` / `ConnectionState` |
| `test_registration` | Duplicate tool/component/handler → `ChatUIRegistrationError` |
| `test_api` | `chat()` facade + `from_env()` |
| `test_public_api` | Import surface smoke |

CI (`.github/workflows/ci.yml`) runs on push/PR against **3.9 · 3.11 · 3.12**.

Coverage gate is configured in `pyproject.toml` (`fail_under`). Agent-loop paths in `agent/loop.py` are the main remaining coverage opportunity (mock provider streams via the `Provider` Protocol).

---

## 8. Packaging

- Build backend: **hatchling**  
- Wheel includes `chatui` package + `ui/index.html` + `ui/css/**` + `ui/vendor/**` + `ui/js/**` (via `force-include`)  
- Optional extras: `groq` / `ollama` / `openai` / `all` / `dev`  
- Console script: `chatui`  
- Vendored JS libs (marked, DOMPurify, highlight.js, github-dark CSS) ship in the wheel — no runtime download, no CDN

License: **MIT** — free for commercial and non-commercial use with attribution via the license notice.

---

## 9. Design law (summary)

From [AGENTS.md](AGENTS.md):

1. **Confident restraint** — fewer borders, more hierarchy  
2. **Strategic color** — one accent; semantic colors for state  
3. **Typography as hierarchy** — serif / sans / mono roles  
4. **Purposeful motion** — ease-out, respect reduced motion  
5. **Accessible by default** — WCAG AA, keyboard, ARIA  

Anti-patterns: glassmorphism-as-decoration, purple-blue “AI slop” gradients, pure black/white, nested cards, bounce easing.

---

## 10. Extension map (for contributors)

| Goal | Start here |
|------|------------|
| New widget type | `widgets.py` + `05-widgets.css` + `buildWidgetHTML` / `bindWidgetEvents` |
| New theme | `themes.py` `_theme(...)` + label maps |
| Tool schema quality | `tools.py` ToolRegistry |
| New LLM provider | `providers/base.py` (implement `Provider`) + `providers/detect.py` |
| Agent loop behavior | `agent/loop.py` |
| Per-connection state | `runtime/connection.py` (`ConnectionState`) |
| History repair | `runtime/history.py` |
| Streaming / provider events | `providers/` adapters → `Event`s |
| CSS / layout | `ui/css/*` + `assets.py` |
| Vendored JS | `ui/vendor/*` (no CDN) |
| A11y | `index.html` landmarks + `00-tokens.css` focus/skip |
| Tests | `tests/` mirroring the module |

---

## 11. Open-source contribution notes

- Prefer small PRs with tests when behavior changes  
- Don’t add a Node build step unless the project consciously changes its USP  
- Don’t introduce CDN dependencies — vendor libs under `ui/vendor/`  
- Keep demos honest about mock vs real data  
- Match AGENTS.md for visual changes  
- Update this file when you change wire protocol, module boundaries, or asset pipeline  

### Suggested roadmap (aligned with README)

1. Real demo integrations  
2. Richer tool schemas / optional Pydantic  
3. More robust component detection  
4. Optional durable conversation storage  
5. Multimodal input  
6. Deeper WS/agent-loop tests  

---

## 12. Quick mental model

- **One process** — Python owns server + UI assembly  
- **One socket** — all realtime traffic is JSON over `/ws` (`protocol_version: 1`)  
- **One loop** — `agent/loop.py` consumes `Event`s from any `Provider`  
- **Per-connection state** — `ConnectionState` owns session, history, system_prompt, stop  
- **Widgets are data** — Python returns structures; JS renders and events flow back  
- **Themes are tokens** — OKLCH CSS variables, switched live  
- **No CDN** — vendored JS ships in the wheel  
- **Open source** — MIT, tests, CI, design docs, contributions welcome  

If you can explain a button click from DOM → WebSocket → handler → optional model turn, you understand ChatUI.

---

*This document is the architecture source of truth for the current tree. When code and docs disagree, fix one of them — preferably both.*
