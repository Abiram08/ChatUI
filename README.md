# ChatUI

**The fastest way to ship a production AI chatbot. One import, three lines.**

ChatUI gives any LLM a premium, production-ready browser interface. Think Streamlit, but purpose-built for chatbots — no page reloads, real-time streaming, zero frontend code.

```bash
pip install -e .
pip install openai          # needed for Groq, Ollama, OpenAI
```

---

## 3 lines to a professional chatbot

Get a free Groq API key at [console.groq.com](https://console.groq.com) (30 seconds, no card):

```bash
export GROQ_API_KEY=gsk_...
```

```python
from chatui import ChatUI

ChatUI(provider="groq").run()
```

Browser opens at `http://localhost:8000`. That's it.

---

## What you can build

### `@app.tool` — Give the AI hands

Any Python function becomes an AI-callable tool. Type hints become the schema automatically.

```python
@app.tool
def get_weather(city: str) -> dict:
    """Get current weather for any city."""
    return {"city": city, "temp": "24\u00b0C", "condition": "Sunny"}
```

### `@app.component` — Give the AI a canvas

When the AI returns `{"component": "chart", "data": {...}}`, your Python function renders HTML directly in the chat.

```python
@app.component("chart")
def render_chart(data: dict) -> str:
    labels, values = data.get("labels", []), data.get("values", [])
    mx = max(values) if values else 1
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0">'
        f'<span style="width:80px;text-align:right;font-size:12px;color:var(--text-secondary)">{l}</span>'
        f'<div style="height:24px;background:var(--accent);border-radius:4px;width:{max(int(v/mx*240), 4)}px"></div>'
        f'<span style="font-size:12px;color:var(--text-primary)">{v}</span></div>'
        for l, v in zip(labels, values)
    )
    return f'<div><b>{data.get("title", "")}</b><br><br>{bars}</div>'
```

### `@app.context` — Give the AI your data

Runs before every message. Its return value gets injected into the AI's context.

```python
@app.context
def my_data():
    """Current sales figures."""
    return df.to_dict()
```

### `app.session` — Persistent state (like `st.session_state`)

State that survives across conversation turns within a connection:

```python
@app.tool
def remember(key: str, value: str):
    app.session[key] = value
    return {"stored": key}

@app.context
def inject_session():
    return dict(app.session)
```

### `@app.on` — Event handlers

Handle widget clicks, file uploads, and custom events:

```python
@app.on("button_click")
def handle_button(data: dict):
    key = data.get("key", "")
    return {"clicked": key}
```

### Widgets — Interactive UI elements

```python
from chatui.widgets import button, table, metric, progress, status

@app.tool
def show_dashboard():
    return (
        metric("Revenue", "$1.2M", delta="+12%"),
        progress(0.78, label="Project completion"),
        status("Syncing database...", state="complete"),
    )
```

Available widgets: `button`, `text_input`, `selectbox`, `radio`, `checkbox`, `slider`, `progress`, `status`, `table`, `markdown`, `html`, `image`, `divider`, `metric`, `expander`, `toast`, `file_uploader`, `spinner`.

---

## Options

```python
ChatUI(
    provider       = "groq",                    # groq | anthropic | ollama | openai
    api_key        = os.getenv("GROQ_API_KEY"),
    model          = "llama-3.3-70b-versatile",
    title          = "My Assistant",
    logo           = "\u2726",
    subtitle       = "Powered by Groq",
    welcome_title  = "What shall we<br>work on?",
    chips          = ["Hello", "Help"],
    theme          = "manuscript",
    system_prompt  = "You are a helpful assistant.",
    port           = 8000,
    open_browser   = True,
    cors_origins   = ["*"],                     # CORS settings
    rate_limit     = 60,                        # requests per minute (0 = disabled)
    log_level      = "info",                    # debug | info | warning | error
    auth_key       = None,                      # Bearer token authentication
).run()
```

### Themes (9 hand-tuned OKLCH palettes)

`manuscript` · `atoll` · `grain` · `ink` · `obsidian` · `nocturne` · `rose` · `mint` · `midnight`

Settings panel allows live theme switching, font selection (Sora / Cormorant / Mono), and text size adjustment — no restart needed.

---

## Production features

| Feature | Description |
|---|---|
| **Session State** | `app.session` — dict-like state per WebSocket connection |
| **Authentication** | Bearer token auth via `auth_key` parameter |
| **Rate Limiting** | Configurable requests/min via `rate_limit` |
| **CORS** | Configurable origins via `cors_origins` |
| **Health Check** | `GET /health` returns provider, model, tool count, etc. |
| **Logging** | Configurable log level, structured format |
| **Widget System** | 18 interactive widget types |
| **Event Handlers** | `@app.on("event")` for widget callbacks |
| **Responsive** | Full mobile support with collapsible sidebar |
| **Accessibility** | ARIA labels, keyboard navigation, screen reader support |
| **Export/Import** | Markdown export, file import |
| **Conversation Persistence** | localStorage with session management |
| **9 Themes** | OKLCH-based, WCAG AA contrast ratios |
| **No Build Step** | Single-file frontend, zero Node.js required |

---

## CLI

```bash
chatui --provider groq --port 3000 --theme obsidian --log-level debug
```

```
usage: chatui [-h] [--provider {anthropic,ollama,groq,openai}] [--model MODEL]
              [--port PORT] [--host HOST] [--theme THEME] [--title TITLE]
              [--log-level {debug,info,warning,error}] [--auth-key AUTH_KEY]
              [--no-browser] [--version]
```

---

## How it works

```
  app.run()
     |
     +-- starts FastAPI server on localhost:8000
     +-- opens browser
              |
              |  loads index.html  (single file, no build step)
              |
              v
     WebSocket connects to /ws
              |
              |  user sends a message
              v
     server calls the AI provider (streaming)
              |
     +----------+--------------------------+
     |          |                          |
     v          v                          v
  plain     tool call               component JSON
  text      detected                detected
     |          |                          |
  tokens    @app.tool fn            @app.component fn
  stream    runs in Python          runs in Python
  to        result -> back to AI    returns HTML
  browser   AI continues            browser renders it
```

Everything runs in a single Python process. No separate frontend server. No Node.js. No build step.

---

## Providers

```python
ChatUI(provider="groq",      api_key=os.getenv("GROQ_API_KEY"))   # free cloud
ChatUI(provider="ollama",    model="llama3")                       # free local, no key
ChatUI(provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY"))
ChatUI(provider="openai",    api_key=os.getenv("OPENAI_API_KEY"))
```

---

## Project structure

```
chatui/
+-- chatui/
|   +-- __init__.py       exports ChatUI, CLI entry
|   +-- server.py         FastAPI app, WebSocket, AI provider routing, middleware
|   +-- themes.py         9 hand-tuned OKLCH themes
|   +-- tools.py          ToolRegistry and ComponentRegistry
|   +-- session.py        Per-connection SessionState
|   +-- widgets.py        18 interactive widget builders
|   +-- ui/
|       +-- index.html    the entire frontend — HTML, CSS, and JS
+-- demo/
|   +-- demo_groq.py      minimal 3-line starter
|   +-- demo_full.py      full showcase: tools, components, widgets, events
+-- pyproject.toml
+-- requirements.txt
+-- LICENSE
```

MIT License
