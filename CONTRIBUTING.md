# Contributing

Thank you for considering contributing to ChatUI. This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/chatui/chatui
cd chatui
pip install -e .
```

## Project Structure

```
chatui/          # Python library
  __init__.py    # Public API
  _server.py     # WebSocket server + FastAPI app
  themes/        # Color themes
  ui/            # Frontend assets
    index.html   # HTML template
    css/         # CSS partials
    js/          # JavaScript
    vendor/      # Third-party JS
demo/            # Example scripts
tests/           # Pytest suite
```

## Running Tests

```bash
pip install pytest httpx websockets
pytest
```

## Code Style

- Python: follow PEP 8, use type hints
- CSS: use OKLCH colors, 2-space indent
- JS: use `const`/`let`, template literals, no semicolons

## Pull Requests

1. Fork the repo
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description

## Adding a Theme

Add to `chatui/themes/palettes.py`:

```python
"my_theme": {
    "mode": "dark",
    "--bg-base": "oklch(...)",
    "--accent": "oklch(...)",
    # ... see existing themes for all required keys
}
```

## Adding a Layout

Add the layout class to `chatui/ui/index.html` body, CSS to `chatui/ui/css/01-layout.css`, and JS support to `chatui/ui/js/app.js`.
