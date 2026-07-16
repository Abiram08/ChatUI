# ChatUI

A simple Python library for building AI chatbot UIs.

No React. No frontend build. Write Python, get a streaming chat interface.

```python
from chatui import chat
chat()
```

> **Status:** early project (v0.2) — useful already, still growing. Feedback and PRs welcome.

---

## Install

```bash
pip install -e ".[dev]"   # from this repo
# later: pip install chatui
```

Optional provider packages:

```bash
pip install "chatui[groq]"       # or openai / anthropic / all
```

---

## Quick start

### 1. Set an API key (or use Ollama)

```bash
# Linux / macOS
export GROQ_API_KEY=...

# Windows PowerShell
$env:GROQ_API_KEY="..."
```

Or run [Ollama](https://ollama.com) locally (no key needed).

### 2. Hello world

```python
from chatui import chat
chat(title="My Bot")
```

Open http://127.0.0.1:8000

### 3. Add tools

```python
from chatui import chat

def get_weather(city: str) -> dict:
    """Current weather for a city."""
    return {"city": city, "temp": "22C"}

chat(tools=[get_weather], title="Weather Bot")
```

### 4. No API key (custom reply)

```python
from chatui import chat

def echo(message: str, session) -> str:
    return f"You said: {message}"

chat(reply=echo, title="Echo Bot")
```

### 5. More control

```python
from chatui import ChatUI

app = ChatUI(provider="groq", title="Agent")

@app.tool
def search(query: str) -> str:
    """Search something."""
    return f"Results for {query}"

app.run()
```

---

## Demos

```bash
python demo/demo_echo.py       # no API key
python demo/demo_beginner.py   # tools
python demo/demo_groq.py       # Groq
python demo/demo_widgets.py    # widgets
python demo/demo_full.py       # tools + widgets + events
```

---

## Features (today)

- One-liner `chat()` API
- Streaming replies over WebSocket
- Tools / function calling
- Widgets (buttons, forms, metrics, tables, …)
- Themes + conversation history in the browser
- Works with Groq, OpenAI, Anthropic, Ollama

---

## Project layout

```
chatui/     # the library
demo/       # examples you can run
tests/      # pytest
```

More detail for contributors: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) if you want to help.

---

## Config tips

```python
chat(
    provider="auto",          # auto | groq | openai | anthropic | ollama
    theme="manuscript",       # try: one_dark, ayu_light, catppuccin_mocha
    port=8000,
    auth_key=None,            # set a secret if you expose it publicly
)
```

Copy [`.env.example`](.env.example) → `.env` for local keys (never commit `.env`).

---

## License

[MIT](LICENSE) — free to use and modify.

This is a **budding** open project: the API may still change before 1.0.
See [CHANGELOG.md](CHANGELOG.md) for what changed recently.
