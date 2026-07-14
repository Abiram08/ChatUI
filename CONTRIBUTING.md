# Contributing to ChatUI

Thank you for helping build **ChatUI** — an open-source (MIT) Python UI library for production AI chatbots.

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/chatui.git
cd chatui
pip install -e ".[dev]"
pytest --cov=chatui
```

## Guidelines

1. **Keep the USP** — one Python process, no required Node/frontend build.
2. **Design** — follow [AGENTS.md](AGENTS.md) for UI/visual changes.
3. **Architecture** — read [ARCHITECTURE.md](ARCHITECTURE.md) before large changes.
4. **Tests** — add or update tests for behavior changes; run `pytest`.
5. **Docs** — update README / ARCHITECTURE when public API or structure changes.
6. **PRs** — small, focused, with a clear description of *why*.

## Good first contributions

- Replace demo mock tools with real, documented integrations
- Improve tool JSON Schema generation
- Accessibility and UX copy polish
- More tests (especially WebSocket / agent loops with mocks)
- Examples and documentation

## Code of conduct (short)

Be respectful. Assume good intent. No harassment or personal attacks.  
This is a community project — collaboration over ego.

## License

By contributing, you agree your contributions are licensed under the same **MIT License** as the project ([LICENSE](LICENSE)).
