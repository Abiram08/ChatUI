# Architecture (short)

How ChatUI is put together — for people hacking on the code.

## Big picture

```
Browser (chatui/ui/)  ←WebSocket→  FastAPI (chatui/server/)
                                      ↓
                              agent loop + tools
                                      ↓
                         providers (Anthropic / OpenAI-compat)
```

One Python process. No Node build. CSS/JS ship inside the package.

## Main modules

| Module | Role |
|--------|------|
| `chatui/api.py` | `chat()` — one-liner API |
| `chatui/app.py` | `ChatUI` config, tools, components, events |
| `chatui/server/builder.py` | FastAPI app, static assets, HTML |
| `chatui/server/ws.py` | WebSocket protocol + chat loop wiring |
| `chatui/agent/loop.py` | Shared agent / tool-call loop |
| `chatui/providers/` | LLM adapters (`anthropic`, `openai_compat`, `detect`) |
| `chatui/runtime/` | Per-connection state + history helpers |
| `chatui/widgets.py` | Widget builders |
| `chatui/tools.py` | Tool + component registries |
| `chatui/themes/` | Theme tokens |
| `chatui/ui/` | `index.html`, CSS partials, JS, vendored libs |

## Request flow

1. `GET /` → HTML + concatenated CSS + theme vars  
2. Browser opens `WS /ws`  
3. Server sends `config`, tools list, session  
4. Client sends `{ "action": "chat", "message": "..." }`  
5. Agent loop streams `token` / `tool_call` / `widgets` / `end`  
6. Past chats call `set_history` so the server has context again  

## WebSocket actions (client → server)

`chat` · `stop` · `regenerate` · `clear` · `set_history` · `widget_event` · `update_system` · session get/set

## Frontend

- `ui/js/app.js` — connection, messages, history, settings  
- `ui/js/widgets.js` — widget rendering  
- `ui/js/markdown.js` — marked + DOMPurify + code copy  
- `ui/css/*.css` — order listed in `manifest.txt`  

## Design preferences

- Chat-first UI (not a generic dashboard framework)
- Safe defaults: sanitize markdown, don’t put secrets in HTML
- Keep `chat()` easy for beginners

## Tests

```bash
pytest
```

Coverage focuses on Python packages; UI is checked via demos + asset tests.
