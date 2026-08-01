# Architecture

ChatUI is a Python library that serves a real-time chat UI over HTTP + WebSocket — no frontend build step required.

## Overview

```
┌─────────────┐     HTTP/WS      ┌──────────────┐
│   Browser   │ ◄──────────────► │   Python      │
│  (vanilla   │                  │   Server      │
│   HTML/CSS/JS│                  │  (FastAPI)    │
└─────────────┘                  └──────┬───────┘
                                        │
                                  ┌─────▼──────┐
                                  │  reply()    │
                                  │  handler    │
                                  └────────────┘
```

## Server (`chatui/_server.py`)

- `ChatUI` class manages a FastAPI application
- `GET /` serves the assembled HTML page with theme CSS injected
- `GET /health` returns `{"status": "ok"}`
- `WS /ws` handles real-time chat via JSON messages
- Static files mounted at `/vendor/` and `/js/`

## Frontend (`chatui/ui/`)

- **`index.html`** — single HTML template with `{{PLACEHOLDERS}}` for server-side values
- **`css/`** — modular CSS partials assembled by `assets.py`
- **`js/app.js`** — all frontend logic (WebSocket, rendering, conversations, settings)
- **`vendor/`** — vendored third-party libraries (marked, DOMPurify, highlight.js)

### CSS Partials

| File | Content |
|------|---------|
| `00-base.css` | Reset, variables, base typography |
| `01-layout.css` | Sidebar, main, tabs, settings panel |
| `02-messages.css` | Messages, welcome screen, markdown |
| `03-composer.css` | Input area, toasts, connection banner |
| `04-responsive.css` | Responsive breakpoints, print, touch |

## Themes (`chatui/themes/`)

- `palettes.py` — 4 themes defined in OKLCH color space
- `__init__.py` — registry with `get_css_vars()` and `get_themes_json()`

## Asset Pipeline (`chatui/ui/assets.py`)

CSS partials are concatenated at serve time (cached). The HTML template is cached in memory. Theme variables are injected before CSS so they cascade correctly.
