# Demos

Run from the repo root after `pip install -e ".[dev]"`:

| Script | What | Needs key? |
|--------|------|------------|
| `demo_echo.py` | Custom reply | No |
| `demo_beginner.py` | Tools with plain functions | Yes / Ollama |
| `demo_groq.py` | Small Groq example | `GROQ_API_KEY` |
| `demo_widgets.py` | Widgets | Optional |
| `demo_full.py` | Tools + widgets + events | Yes / Ollama |

```bash
python demo/demo_echo.py
```
