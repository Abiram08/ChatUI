# ChatUI

A Python package that gives any AI chatbot a premium browser interface. You write Python, the UI handles itself.

Not on PyPI yet — install directly from GitHub:

```bash
git clone https://github.com/YOUR_USERNAME/chatui.git
cd chatui
pip install -e .
pip install openai          # needed for Groq, Ollama, OpenAI
```

---

Get a free Groq API key at [console.groq.com](https://console.groq.com) (30 seconds, no card). Then:

```bash
export GROQ_API_KEY=gsk_...
```

```python
import os
from chatui import ChatUI

ChatUI(
    provider = "groq",
    api_key  = os.getenv("GROQ_API_KEY"),
    title    = "My Assistant",
).run()
```

Browser opens at `http://localhost:8000`.

---

## The three things you can add

**`@app.tool` — give the AI hands**

Any function becomes an AI tool. When it's called, a live card appears in the chat showing the inputs and result — not raw JSON, not plain text.

```python
@app.tool
def get_weather(city: str) -> dict:
    """Get current weather for any city."""
    return {"city": city, "temp": "24°C", "condition": "Sunny"}
```

**`@app.component` — give the AI a canvas**

When the AI responds with `{"component": "chart", "data": {...}}`, your function renders HTML directly inside the chat bubble. Charts, tables, anything.

```python
@app.component("chart")
def render_chart(data: dict) -> str:
    """Bar chart."""
    labels, values = data.get("labels", []), data.get("values", [])
    mx = max(values) if values else 1
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<span style="width:80px;text-align:right;font-size:12px;color:var(--text-secondary)">{l}</span>'
        f'<div style="height:20px;background:var(--accent);border-radius:3px;width:{int(v/mx*220)}px"></div>'
        f'<span style="font-size:12px;color:var(--text-primary)">{v}</span></div>'
        for l, v in zip(labels, values)
    )
    return f'<div><b style="font-size:13px">{data.get("title","")}</b><br><br>{bars}</div>'
```

**`@app.context` — give the AI your data**

Runs before every message. Whatever it returns gets injected into the AI's context automatically. No copy-pasting data into the chat.

```python
@app.context
def my_data():
    """Current sales figures."""
    return df.to_dict()
```

---

## Options

```python
ChatUI(
    provider      = "groq",              # groq | anthropic | ollama | openai
    api_key       = os.getenv("GROQ_API_KEY"),
    model         = "llama-3.3-70b-versatile",
    title         = "My Assistant",
    logo          = "✦",                 # emoji or symbol shown in sidebar + welcome
    subtitle      = "Powered by Groq",   # line under title on welcome screen
    chips         = ["Hello", "Help"],   # quick-start buttons (leave out to hide)
    theme         = "tokyonight",
    system_prompt = "You are a helpful assistant.",
    port          = 8000,
).run()
```

Themes: `tokyonight` · `darkside` · `rosepine` · `gruvbox` · `catppuccin` · `nord` · `ayu`

The settings panel (⚙ in sidebar) has a Themes dropdown, font toggle, and text size — all live, no restart needed.

---

## How it works

```
  app.run()
     │
     ├─ starts FastAPI server on localhost:8000
     └─ opens browser
               │
               │  loads index.html  (HTML + CSS + JS — one file, no build step)
               │
               ▼
     WebSocket connects to /ws
               │
               │  user sends a message
               ▼
     server calls the AI provider (streaming)
               │
     ┌─────────┼──────────────────────────┐
     │         │                          │
     ▼         ▼                          ▼
  plain     tool call               component JSON
  text      detected                detected
     │         │                          │
  tokens    @app.tool fn            @app.component fn
  stream    runs in Python          runs in Python
  to        result → back to AI     returns HTML
  browser   AI continues            browser renders it
                                    in the chat bubble
```

Everything — the AI provider, your tools, your components, and the WebSocket — runs in the same Python process. No separate frontend server. No Node.js. No build step.

---

## Project structure

```
chatui/
├── chatui/
│   ├── __init__.py       exports ChatUI
│   ├── server.py         FastAPI app, WebSocket handler, AI provider routing
│   ├── themes.py         7 theme definitions as CSS variable dicts
│   ├── tools.py          ToolRegistry and ComponentRegistry
│   └── ui/
│       └── index.html    the entire frontend — HTML, CSS, and JS in one file
├── demo/
│   ├── demo_groq.py      minimal starter
│   └── demo_full.py      with tools and a chart component
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

**About `chatui.egg-info/`**

This folder appears automatically in your local directory when you run `pip install -e .` (editable install). It is pip's metadata cache — package name, version, and dependencies. It is not part of the project and is already blocked from git by `.gitignore`. You will see it locally but it will never appear in the GitHub repository.

---

## Providers

```python
ChatUI(provider="groq",      api_key=os.getenv("GROQ_API_KEY"))   # free cloud
ChatUI(provider="ollama",    model="llama3")                       # free local, no key
ChatUI(provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY"))
ChatUI(provider="openai",    api_key=os.getenv("OPENAI_API_KEY"))
```



MIT License
