<div align="center">

# ChatUI

**Open-source UI library for AI chatbots.**

Write Python, get a streaming chat interface. No frontend build required.

[![CI](https://img.shields.io/github/actions/workflow/status/chatui/chatui/ci.yml?branch=main&label=CI&logo=github)](https://github.com/chatui/chatui/actions)
[![PyPI](https://img.shields.io/pypi/v/chatui?label=PyPI&logo=pypi)](https://pypi.org/project/chatui/)
[![Python](https://img.shields.io/pypi/pyversions/chatui?logo=python)](https://pypi.org/project/chatui/)
[![License](https://img.shields.io/github/license/chatui/chatui?label=License)](LICENSE)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

```python
from chatui import chat

def echo(message, session):
    return f"You said: {message}"

chat(reply=echo)
```

</div>

---

## Why ChatUI?

- **Gradio/Streamlit-style API** — one function call, instant chat UI
- **2 layouts** — sidebar (default) or tabs
- **4 themes** — dark (Cursor-inspired), light, sepia, slate
- **Streaming** — sync/async generators for token-by-token output
- **Zero frontend build** — pure vanilla HTML/CSS/JS served over FastAPI
- **Conversation history** — persisted in browser localStorage
- **Markdown + code highlighting** — built-in with marked + highlight.js

## Install

```bash
pip install chatui
```

Or from source:

```bash
git clone https://github.com/chatui/chatui
cd chatui
pip install -e .
```

## Quickstart

### Echo bot (no LLM needed)

```python
from chatui import chat

def echo(message, session):
    return f"You said: {message}"

chat(reply=echo, title="Echo Bot")
```

Open [http://localhost:8000](http://localhost:8000)

### Streaming (generator)

```python
from chatui import chat

def stream(message, session):
    words = f"You said: {message}".split()
    for word in words:
        yield word + " "

chat(reply=stream, title="Streaming Bot")
```

### Async

```python
import asyncio
from chatui import chat

async def async_bot(message, session):
    await asyncio.sleep(0.3)
    return f"Async reply: {message}"

chat(reply=async_bot)
```

### Async generator

```python
import asyncio
from chatui import chat

async def async_stream(message, session):
    for ch in message:
        yield ch.upper()
        await asyncio.sleep(0.05)

chat(reply=async_stream)
```

## API Reference

### `chat()`

The simplest way to start a chat UI.

```python
chat(
    reply=handler,          # Your message handler (required)
    title="Chat",           # Page title
    subtitle="",            # Subtitle below welcome heading
    logo="◆",              # Logo character
    welcome_title="What can I help with?",  # Welcome heading
    layout="sidebar",       # "sidebar" | "tabs"
    theme="dark",           # "dark" | "light" | "sepia" | "slate"
    chips=None,             # List[str] — suggested prompts
    host="0.0.0.0",         # Bind address
    port=8000,              # Bind port
)
```

### `ChatUI`

Programmatic API for more control.

```python
from chatui import ChatUI

app = ChatUI(reply=handler, title="My Bot")
app.run(host="127.0.0.1", port=8080)

# Or mount on an existing FastAPI app
parent_app.mount("/chat", app.app)
```

### Reply handlers

| Type | Signature | Use Case |
|------|-----------|----------|
| Sync function | `def fn(msg, session) -> str` | Simple replies |
| Async function | `async def fn(msg, session) -> str` | API calls |
| Sync generator | `def fn(msg, session) -> Generator[str]` | Streaming |
| Async generator | `async def fn(msg, session) -> AsyncGenerator[str]` | Async streaming |

## Layouts

| Layout | Description |
|--------|-------------|
| `sidebar` | Conversation list on the left (default) |
| `tabs` | Top tab strip, sidebar opens as drawer |

## Themes

| Theme | Mode | Accent | Vibe |
|-------|------|--------|------|
| `dark` | dark | Blue (#4f8cff) | Cursor-inspired, default |
| `light` | light | Blue | Clean, bright |
| `sepia` | light | Terracotta | Warm, paper-like |
| `slate` | dark | Cyan | Deep blue-black |

Users can switch themes from the Settings panel. Choice persists in localStorage.

## Architecture

```
Browser (vanilla JS) ◄──WebSocket──► Python (FastAPI) ◄──► your reply()
                                          │
                                    GET / → assembled HTML
                                    GET /health → {"status":"ok"}
                                    WS /ws → real-time chat
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Development

```bash
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT — free to use and modify. See [LICENSE](LICENSE).
