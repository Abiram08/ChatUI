# Contributing

Thanks for checking out ChatUI. This is an early project — small, clear PRs help a lot.

## Setup

```bash
git clone <this-repo>
cd ChatUI
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Try the UI without an API key:

```bash
python demo/demo_echo.py
```

## How to help

- Fix bugs or typos
- Improve demos / README
- Add tests
- Small UI polish in `chatui/ui/`
- New provider bits in `chatui/providers/`

Open an issue first for big ideas.

## Guidelines

1. Keep the **beginner path** simple: `from chatui import chat; chat()` should always work.
2. **No Node/npm** for the core UI — edit HTML/CSS/JS in `chatui/ui/` directly.
3. Support **Python 3.9+**.
4. Add a test when you change behavior.
5. Don’t commit API keys or `.env` files.

## Tests

```bash
pytest
```

## Code map

| Path | What it is |
|------|------------|
| `chatui/api.py` | `chat()` helper |
| `chatui/app.py` | main `ChatUI` class |
| `chatui/server/` | HTTP + WebSocket |
| `chatui/agent/` | tool / agent loop |
| `chatui/providers/` | LLM adapters |
| `chatui/ui/` | browser UI assets |
| `demo/` | examples |
| `tests/` | tests |

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deeper walkthrough.

## License

By contributing, you agree your changes are under the MIT License.
