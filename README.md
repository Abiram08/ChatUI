# ChatUI

**Open-source Python UI library for production AI chatbots.**  
One import. Three lines. Premium interface. Zero frontend build.

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/badge/CI-pytest-informational.svg)](.github/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](ARCHITECTURE.md)

ChatUI is the **Streamlit-style alternative for chatbots**: pure Python on the developer side, a professional browser UI for users — streaming replies, tool calling, interactive widgets, themes, and session state. No React app. No Node.js. No page reloads.

| | Streamlit | ChatUI |
|---|---|---|
| Focus | General data apps | **LLM chat & agents** |
| Streaming chat | DIY | **Built-in** |
| Tool / function calling | DIY | **First-class** |
| Frontend build | None | **None** |
| Process model | One Python process | **One Python process** |
| License | Apache-2.0 | **MIT** |

---

## Why ChatUI?

- **Open source (MIT)** — use it, fork it, ship it commercially; contributions welcome.
- **Three-line DX** — `ChatUI(provider="groq").run()` is a full product shell.
- **Premium UI out of the box** — editorial typography, 9 OKLCH themes, accessible controls.
- **Agent-native** — `@app.tool`, `@app.component`, `@app.on`, `app.session`.
- **Library-grade internals** — modular CSS, unit tests, CI, clean public API.

Deep dive: **[ARCHITECTURE.md](ARCHITECTURE.md)** · Design: **[AGENTS.md](AGENTS.md)** · Contribute: **[CONTRIBUTING.md](CONTRIBUTING.md)**

---

## Install

```bash
# From source (recommended while the project is in beta)
git clone https://github.com/YOUR_USERNAME/chatui.git
cd chatui
pip install -e .

# Provider extras (pick what you use)
pip install openai          # groq | ollama | openai
# anthropic is already a core dependency
```

Dev / contributors:

```bash
pip install -e ".[dev]"
pytest --cov=chatui
```

---

## 3 lines to a professional chatbot

Get a free Groq key at [console.groq.com](https://console.groq.com) (no card):

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_..."

# macOS / Linux
export GROQ_API_KEY=gsk_...
```

```python
from chatui import ChatUI

ChatUI(provider="groq").run()
```

Browser opens at `http://localhost:8000`. That’s it.

### Minimal demo with widgets

```python
from chatui import ChatUI, button, metric, progress

app = ChatUI(provider="groq")

@app.tool
def show_stats():
    """Show a small dashboard."""
    return (
        metric("Users", "12.4k", delta="+8%"),
        progress(0.72, label="Quota"),
        button("Refresh", key="refresh"),
    )

@app.on("button_click")
def on_click(data):
    return {"clicked": data.get("key")}

app.run()
```

Full showcase:

```bash
python demo/demo_groq.py    # minimal
python demo/demo_full.py    # tools + components + widgets
```

---

## What you can build

### `@app.tool` — Give the AI hands

Any Python function becomes an AI-callable tool. Type hints become the JSON schema automatically.

```python
@app.tool
def get_weather(city: str) -> dict:
    """Get current weather for any city."""
    return {"city": city, "temp": "24°C", "condition": "Sunny"}
```

### `@app.component` — Give the AI a canvas

When the model returns **only** `{"component": "chart", "data": {...}}`, your Python function renders HTML in the chat.

```python
@app.component("chart")
def render_chart(data: dict) -> str:
    title = data.get("title", "Chart")
    labels = data.get("labels", [])
    values = data.get("values", [])
    # Return trusted HTML using CSS variables from the active theme
    return f"<b style='font-family:var(--font-serif)'>{title}</b>"
```

### `@app.context` — Live data every turn

Runs before each model call. Return value is injected into the system context.

```python
@app.context
def my_data():
    """Current sales figures."""
    return {"revenue": 1_200_000, "users": 34_291}
```

### `app.session` — State like `st.session_state`

Per WebSocket connection, isolated automatically via `contextvars`:

```python
@app.tool
def remember(key: str, value: str):
    """Store a value for this chat session."""
    app.session[key] = value
    return {"stored": key}

@app.context
def inject_session():
    return dict(app.session)
```

### `@app.on` — Widget & custom events

```python
@app.on("button_click")   # any button
@app.on("refresh")        # specific widget key
def handle(data: dict):
    return {"ok": True, "key": data.get("key")}
```

### Widgets — Interactive UI in the stream

```python
from chatui import button, table, metric, progress, status, columns, end_columns

@app.tool
def show_dashboard():
    """Render KPIs and actions."""
    return (
        metric("Revenue", "$1.2M", delta="+12%"),
        metric("Users", "34.2k", delta="+8%"),
        progress(0.78, label="Project completion"),
        status("Database sync complete", state="complete"),
        button("Refresh data", key="refresh"),
        button("Dismiss", key="cancel", variant="secondary"),
    )
```

**Layout behavior (current):**

- Consecutive **buttons** → one action row (centered labels, shared gap)
- Consecutive **metrics** → responsive metric strip
- **columns / end_columns** → CSS `fr` grid (stacks on narrow screens)
- Buttons / dividers / spinners use a **flat** shell (no nested card clutter)

| Widget | Events | Notes |
|--------|--------|--------|
| `button` | `button_click` | `primary` · `secondary` · `danger` |
| `text_input` | `text_input_submit` | Label + **Send** |
| `selectbox` | `selectbox_change` | |
| `radio` | `radio_change` | |
| `checkbox` | `checkbox_change` | |
| `slider` | `slider_change` | |
| `progress` | — | 0.0–1.0 |
| `status` | — | `running` · `complete` · `error` |
| `table` | — | list of row dicts |
| `markdown` / `html` / `image` | — | content blocks |
| `divider` / `spinner` / `toast` | — | chrome |
| `metric` | — | value + optional delta |
| `columns` / `end_columns` | — | layout |
| `expander` / `end_expander` | — | collapsible |
| `file_uploader` | `file_upload` | base64, size-capped |

---

## Options

```python
import os
from chatui import ChatUI

ChatUI(
    provider       = "groq",                    # groq | anthropic | ollama | openai
    api_key        = os.getenv("GROQ_API_KEY"),
    model          = "llama-3.3-70b-versatile",
    title          = "My Assistant",
    logo           = "◆",
    subtitle       = "Powered by Groq",
    welcome_title  = "What shall we<br>work on?",
    chips          = ["Hello", "Help"],
    theme          = "manuscript",
    system_prompt  = "You are a helpful assistant.",
    port           = 8000,
    host           = "0.0.0.0",
    open_browser   = True,
    cors_origins   = ["*"],
    rate_limit     = 60,                        # 0 = off
    log_level      = "info",
    auth_key       = None,                      # Bearer or ?token=
).run()
```

### Themes (9 OKLCH palettes)

| Light | Dark |
|-------|------|
| `manuscript` · `atoll` · `grain` · `rose` · `mint` | `ink` · `obsidian` · `nocturne` · `midnight` |

Live switching in **Settings** (theme, typeface, text size) — no restart.  
Palettes use tinted neutrals (never pure black/white) and an `--accent-fg` token for text on accent buttons.

---

## How it works (current architecture)

```
  app.run()
     │
     ├─ Uvicorn + FastAPI (one process)
     ├─ GET /  → HTML shell + assembled CSS + theme vars
     └─ opens browser
              │
              ▼
     WebSocket /ws
              │
              ▼
     LLM stream (Anthropic or OpenAI-compatible)
              │
     ┌────────┼────────────────┐
     ▼        ▼                ▼
  tokens   @app.tool        component JSON
  → UI     → widgets/JSON   → @app.component HTML
```

**Frontend assembly (no Node):**

1. `chatui/ui/css/*.css` partials are listed in `manifest.txt`
2. `chatui/ui/assets.py` concatenates them at **serve time**
3. Theme OKLCH vars are prepended; placeholders in `index.html` are filled
4. Browser gets one HTML document — still zero build step

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for wire protocol, modules, and extension points.

---

## Providers

```python
ChatUI(provider="groq",      api_key=os.getenv("GROQ_API_KEY"))      # free cloud
ChatUI(provider="ollama",    model="llama3")                          # local, no key
ChatUI(provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY"))
ChatUI(provider="openai",    api_key=os.getenv("OPENAI_API_KEY"))
```

| Provider | Default model | Extra package |
|----------|---------------|---------------|
| `groq` | `llama-3.3-70b-versatile` | `openai` |
| `ollama` | `llama3` | `openai` |
| `anthropic` | Claude Sonnet | (core) |
| `openai` | `gpt-4o` | `openai` |

---

## Production features

| Feature | Description |
|---------|-------------|
| **Streaming** | Token-by-token markdown + code highlighting |
| **Tools** | `@app.tool` with auto schemas (Anthropic + OpenAI formats) |
| **Widgets** | 18 types; layout grouping for buttons/metrics/columns |
| **Components** | Model-driven HTML via `@app.component` |
| **Session** | `app.session` per WebSocket (contextvars) |
| **Auth** | Optional Bearer / `?token=` |
| **Rate limit** | Sliding window on HTTP + chat |
| **Health** | `GET /health` → provider, model, tools, components |
| **Themes** | 9 OKLCH palettes, live switch |
| **A11y** | Skip link, ARIA, keyboard (Esc, Enter, shortcuts), focus rings |
| **Responsive** | Mobile sidebar, touch targets, safe areas |
| **Persistence** | Conversation history in `localStorage` |
| **Export / import** | Markdown |
| **Safety caps** | Message length, file size, tool rounds |
| **Tests + CI** | pytest suite; GitHub Actions on 3.9 / 3.11 / 3.12 |

---

## CLI

```bash
chatui --provider groq --port 3000 --theme obsidian --log-level debug
```

```
usage: chatui [-h] [--provider {anthropic,ollama,groq,openai}] [--model MODEL]
              [--port PORT] [--host HOST] [--theme THEME] [--title TITLE]
              [--log-level {debug,info,warning,error}] [--auth-key AUTH_KEY]
              [--rate-limit N] [--no-browser] [--version]
```

---

## Project structure

```
ChatUI/
├── chatui/
│   ├── __init__.py          # Public API + CLI
│   ├── server.py            # ChatUI, FastAPI, WebSocket, agent loops
│   ├── themes.py            # OKLCH theme builder (9 palettes)
│   ├── tools.py             # ToolRegistry + ComponentRegistry
│   ├── session.py           # SessionState + contextvars
│   ├── widgets.py           # Widget builders + collect/strip
│   └── ui/
│       ├── index.html       # Shell + client JS
│       ├── assets.py        # CSS assembly at serve time
│       └── css/             # 00-tokens … 07-responsive
├── tests/                   # Unit + HTTP smoke tests
├── demo/                    # demo_groq.py, demo_full.py
├── scripts/                 # Maintainer helpers (e.g. split_css)
├── .github/workflows/ci.yml
├── AGENTS.md                # Design system for contributors
├── ARCHITECTURE.md          # Source-of-truth system design
├── LICENSE                  # MIT
├── pyproject.toml
└── README.md
```

---

## Development

```bash
pip install -e ".[dev]"
pytest --cov=chatui
```

| Suite | Covers |
|-------|--------|
| `test_widgets.py` | Builders, collect/strip |
| `test_themes.py` | Palettes, tokens, CSS/JSON export |
| `test_session.py` | SessionState + context binding |
| `test_tools.py` | Tool & component registries |
| `test_assets.py` | Modular CSS assembly |
| `test_server.py` | `/`, `/health`, decorators |
| `test_public_api.py` | Package surface |

CI runs the same suite on **Python 3.9, 3.11, and 3.12**.

---

## Open source

ChatUI is free and open source under the **[MIT License](LICENSE)**.

You can:

- Use it in personal and commercial products
- Modify and redistribute
- Contribute improvements back to the community

### Contributing

1. Fork the repo and create a branch  
2. `pip install -e ".[dev]"`  
3. Make changes; keep design rules in **[AGENTS.md](AGENTS.md)**  
4. `pytest --cov=chatui`  
5. Open a pull request with a clear description  

Good first areas:

- Real demo tool integrations (APIs instead of random mock data)
- Richer tool JSON Schema (param descriptions, enums)
- More tests around the WebSocket agent loops
- Docs, examples, and accessibility polish

### Community

- **Issues** — bugs and feature requests  
- **Pull requests** — welcome; small, focused PRs are easiest to review  
- **Architecture questions** — start with [ARCHITECTURE.md](ARCHITECTURE.md)  

Please be respectful. This is a community project; assume good intent and keep feedback constructive.

### Roadmap (high level)

- [ ] Production-grade example tools (weather, search, etc.)
- [ ] Stronger tool schema generation (Pydantic optional)
- [ ] Robust component protocol (beyond exact-JSON replies)
- [ ] Optional server-side conversation store
- [ ] Multimodal / vision inputs
- [ ] Higher coverage on agent loops

---

## License

MIT © [ChatUI Contributors](LICENSE)

Built in the open so anyone can ship better AI chat UIs — simply, and with taste.
