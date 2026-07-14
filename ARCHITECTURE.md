# ChatUI — Architecture & Source Guide

> **Audience**: contributors, maintainers, and AI assistants working on this **open-source** library.  
> **Goal**: understand the whole system — data flows, modules, UI assembly, and extension points — so changes stay coherent.

**ChatUI** is a MIT-licensed, single-Python-process framework for production LLM chat UIs.  
It competes with “Streamlit for chatbots”: developer writes Python; users get a premium streaming chat interface with tools, widgets, and themes — **no Node.js, no frontend build**.

**Core promise**

```python
from chatui import ChatUI
ChatUI(provider="groq").run()
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
│  • CSS assembled server-side (modular partials, zero Node)          │
│  • WebSocket → /ws                                                  │
│  • Streaming markdown, tool cards, widgets, components              │
│  • localStorage conversations · live theme/font/size                │
└─────────────────────────────────────────────────────────────────────┘
                                ↕ JSON over WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI + Uvicorn  (chatui/server.py)                              │
│  • GET /  → render_html(theme_vars) + template fills                │
│  • GET /health                                                      │
│  • WS /ws · auth · rate limit · logging                             │
│  • SessionState per connection (contextvars)                        │
│  • Agentic loops:                                                   │
│      – _loop_anthropic  (native tool_use)                           │
│      – _loop_openai     (OpenAI tool_calls; groq/ollama/openai)     │
│  • Tool run off event loop · widget side-effects · components       │
└─────────────────────────────────────────────────────────────────────┘
                                ↕
┌─────────────────────────────────────────────────────────────────────┐
│  LLM providers                                                      │
│  anthropic | groq | ollama | openai  (async clients)                │
└─────────────────────────────────────────────────────────────────────┘
```

Everything runs in **one Python process**. Frontend assets ship inside the wheel; CSS is concatenated at request time.

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
│   ├── __init__.py           # Public API + CLI entrypoint
│   ├── server.py             # ChatUI class, FastAPI, WS, agent loops
│   ├── tools.py              # ToolRegistry + ComponentRegistry
│   ├── widgets.py            # Widget + builders + collect/strip
│   ├── session.py            # SessionState + contextvar helpers
│   ├── themes.py             # OKLCH theme factory (9 palettes)
│   └── ui/
│       ├── __init__.py
│       ├── assets.py         # load_css / render_html (no build step)
│       ├── index.html        # Shell + JS; /*{{STYLES}}*/ placeholder
│       └── css/
│           ├── manifest.txt  # Partial order
│           ├── 00-tokens.css
│           ├── 01-shell.css
│           ├── 02-main.css
│           ├── 03-messages.css
│           ├── 04-tools.css
│           ├── 05-widgets.css
│           ├── 06-composer.css
│           └── 07-responsive.css
│
├── tests/                    # Unit + HTTP smoke tests
│   ├── test_widgets.py
│   ├── test_themes.py
│   ├── test_session.py
│   ├── test_tools.py
│   ├── test_assets.py
│   ├── test_server.py
│   └── test_public_api.py
│
├── demo/
│   ├── demo_groq.py          # Minimal starter
│   └── demo_full.py          # Tools, components, widgets, events
│
└── scripts/
    └── split_css.py          # Maintainer helper to re-split CSS
```

**Key insight**: the library stays small. Complexity lives in `server.py` (protocol + agent loop) and the frontend (modular CSS + one JS shell). Python modules stay focused and testable.

---

## 3. Python modules

### 3.1 `chatui/__init__.py`

Public surface for open-source consumers:

- `ChatUI`, `SessionState`, `VERSION`, `Widget`
- All widget builders (`button`, `metric`, …)
- CLI: `python -m` / `chatui` → `main()`

### 3.2 `chatui/session.py`

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

### 3.3 `chatui/tools.py`

#### ToolRegistry

- Reads docstring (first line = model description), signature, type hints
- Builds Anthropic `input_schema` and OpenAI `function.parameters`
- `execute(name, inputs)` **never raises** to the model → `{"error": ...}`

**Known limitation (open for contributions):** schemas are basic (no per-param descriptions, enums, or constraints). Optional Pydantic integration is a natural extension.

#### ComponentRegistry

When the model emits **exactly**:

```json
{"component": "dashboard", "data": {...}}
```

the registered Python renderer returns an HTML string injected as a component card.

### 3.4 `chatui/widgets.py`

- `Widget` — small container (`type`, `id`, `props`) + `to_payload()`
- Builders return widgets; tools/handlers may return one widget, a sequence, or mix of widgets + data
- `collect_widgets` — recursive extract  
- `strip_widgets` — JSON-safe value for the model  
- Pure widget returns become `{"ok": true, "ui": ["button", ...]}`

Layout intent (enforced in the frontend renderer):

| Pattern | UI result |
|---------|-----------|
| Consecutive `button`s | `.w-actions` row |
| Consecutive `metric`s | `.w-metrics` strip |
| `columns` … `end_columns` | CSS `fr` grid |
| `button` / `divider` / `spinner` alone | `.widget-card.flat` |

### 3.5 `chatui/themes.py`

Themes are built by a shared `_theme(mode, hue=…, accent_hue=…)` factory (DRY, clean-code).

- 5 light + 4 dark
- Tinted neutrals only (no pure `#000` / `#fff`)
- Tokens include `--accent-fg` for text *on* accent surfaces
- `get_css_vars(name)` → `:root { … }` for SSR injection  
- `get_themes_json()` → client-side live switcher

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

### 3.6 `chatui/ui/assets.py`

Zero-build asset pipeline:

1. Read `css/manifest.txt`
2. Concatenate partials (with file banners for debugging)
3. Prepend theme vars
4. Replace `/*{{STYLES}}*/` in `index.html`

`load_css()` is cached (`lru_cache`); `clear_asset_cache()` exists for tests.

### 3.7 `chatui/server.py` (core)

#### Init

- Resolve provider + default model  
- Build `AsyncAnthropic` or `AsyncOpenAI` (base_url for groq/ollama)  
- `ToolRegistry`, `ComponentRegistry`, event map  
- FastAPI: CORS, optional auth, optional rate limit, logging  
- Routes: `GET /`, `GET /health`, `WebSocket /ws`

#### Agentic loops

**Anthropic** — stream + `tool_use` blocks; loop until end or max rounds.  
**OpenAI-compatible** — stream + `tool_calls` by index; same widget/component side effects.

Shared:

- `MAX_TOOL_ROUNDS = 12`
- Tools via `asyncio.to_thread` + session rebinding  
- Widgets emitted as `{type: "widgets", …}` then stripped for the model  
- History truncated to `MAX_HISTORY_TURNS * 2` messages  

#### WebSocket

Per connection:

1. New `SessionState`, bind contextvar  
2. Send `config`, `tools_ready`, `components_ready`, `session_state`  
3. Dispatch: `chat` · `widget_event` · `regenerate` · `stop` · `clear` · `update_system` · session get/set  

Widget handlers register under **event type** and **widget key**.

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
| `assets.py` | Assemble at serve time |

Still **no Node**, no Vite/Webpack. Maintainability comes from partials + manifest, not a JS toolchain.

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

**Client → server**

| Action | Purpose |
|--------|---------|
| `chat` | User message |
| `widget_event` | Button, input, upload, etc. |
| `regenerate` | Redo last assistant turn |
| `stop` | Cancel generation |
| `clear` | Reset server history |
| `update_system` | New system prompt |
| `set_session` / `get_session` | Session bridge |

**Server → client**

| Type | Purpose |
|------|---------|
| `config`, `tools_ready`, `components_ready`, `session_state` | Bootstrap |
| `start` / `start_again` | Stream begin |
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
2. Server appends user message → agent loop  
3. Model calls `show_widgets`  
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
| `test_themes` | Token completeness, no pure black/white, export |
| `test_session` | Dict API + contextvar bind/reset |
| `test_tools` | Schema gen, execute errors, components |
| `test_assets` | Manifest + CSS/HTML assembly |
| `test_server` | `/health`, `/` HTML, rate limiter, decorators |
| `test_public_api` | Import surface smoke |

CI (`.github/workflows/ci.yml`) runs on push/PR against **3.9 · 3.11 · 3.12**.

Coverage gate is configured in `pyproject.toml` (`fail_under`). Agent-loop paths in `server.py` are the main remaining coverage opportunity (mock LLM streams).

---

## 8. Packaging

- Build backend: **hatchling**  
- Wheel includes `chatui` package + `ui/index.html` + `ui/css/**`  
- Optional extras: `groq` / `ollama` / `openai` / `all` / `dev`  
- Console script: `chatui`  

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
| Streaming / providers | `server.py` `_loop_*` |
| CSS / layout | `ui/css/*` + `assets.py` |
| A11y | `index.html` landmarks + `00-tokens.css` focus/skip |
| Tests | `tests/` mirroring the module |

---

## 11. Open-source contribution notes

- Prefer small PRs with tests when behavior changes  
- Don’t add a Node build step unless the project consciously changes its USP  
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
- **One socket** — all realtime traffic is JSON over `/ws`  
- **Two loops** — Anthropic vs OpenAI-shaped tool calling  
- **Widgets are data** — Python returns structures; JS renders and events flow back  
- **Themes are tokens** — OKLCH CSS variables, switched live  
- **Open source** — MIT, tests, CI, design docs, contributions welcome  

If you can explain a button click from DOM → WebSocket → handler → optional model turn, you understand ChatUI.

---

*This document is the architecture source of truth for the current tree. When code and docs disagree, fix one of them — preferably both.*
