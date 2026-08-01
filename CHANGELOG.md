# Changelog

## 0.3.0 (2026-07-29)

### Major
- Complete rewrite: stripped to core (2 layouts, 4 themes, Gradio-like API)
- Removed: providers system, agent loop, widgets, tools, rate limiter
- New Cursor-inspired UI design

### Features
- `chat()` function — one-liner to start a chat UI
- `ChatUI` class for programmatic use
- 2 layouts: `sidebar` (default), `tabs`
- 4 themes: `dark`, `light`, `sepia`, `slate`
- Streaming support (sync/async generators)
- Markdown rendering with code highlighting
- Conversation history in localStorage
- Settings panel (theme, font switching)
- Keyboard shortcuts (Enter to send, Ctrl+K for sidebar)

### Engineering
- FastAPI + WebSocket architecture
- OKLCH color tokens for perceptual uniformity
- Modular CSS with manifest-based assembly
- Pure vanilla JS frontend (no framework)
- Conversation persistence in browser

## 0.2.0 (2026-06-15)

- Initial public release
- Provider system (Groq, OpenAI, Anthropic, Ollama)
- Widget system (buttons, metrics, tables, etc.)
- Tool/function calling support
