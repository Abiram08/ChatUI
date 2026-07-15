# ChatUI — Launch Plan

> Updated execution plan to take the current beta to a **100 % launchable product**.
>
> **Product thesis:** The Streamlit alternative for Python chatbots — premium UI, agent-native, zero frontend build, easy enough for beginners.
>
> **Status:** Beta `0.1.0` → target **L0 soft launch**, then **L1 public beta**, then **L2 1.0**.

---

## How to use this doc

- Checkboxes are the source of truth.
- Prefer small PRs that map to one subsection.
- Keep the public API stable when refactoring internals.
- Design changes must follow **AGENTS.md**.
- Architecture changes must update **ARCHITECTURE.md**.
- Update this file when tasks complete.

**Legend**

| Priority | Meaning |
|----------|---------|
| P0 | Launch blocker — ship stops without this |
| P1 | Launch polish — expected for public beta |
| P2 | Quality / maintainability — expected for 1.0 |
| P3 | Production hardiness |
| P4 | Ecosystem — after core is solid |

---

## 0. What "launchable" means

A launchable ChatUI must:

1. Install in one command (`pip install chatui` or `pip install git+...`).
2. Run from a 1-liner (`from chatui import chat; chat()`).
3. Be visually premium (Zed-class themes, no AI slop).
4. Be safe by default (no secrets in HTML, sanitized markdown, honest auth patterns).
5. Have honest demos and clear docs.
6. Be deployable (Docker recipe + at least one cloud one-pager).
7. Have a stable, tested public API.

---

## 1. Current state snapshot

| Area | Current state | Launch target |
|------|---------------|---------------|
| Beginner API | `chat()` works, auto provider works, plain `tools=[...]` works | Polish + expose in `__all__` |
| Tools / components | Rich schemas, dict registration, decorators | Add HITL + sanitizer docs |
| Widgets / layout | `actions/row/stack/card`, `choice/form/confirm` | Add welcome chips + round-trip tests |
| Themes | All Zed/editor themes + aliases in one module | Move to package + canonical defaults |
| Architecture | New packages exist but `server.py` still runs old loops | Wire adapters + delete old loops |
| Security | Auth token out of HTML, markdown sanitized | CORS warning + SECURITY.md examples |
| Tests | `pytest` green, ~45 % coverage | Raise to 70 %+ with agent/provider tests |
| Deploy | No Docker, no deploy guides, `lite=True` ignored | Docker + guides + wired lite mode |
| Docs | Good README, CHANGELOG, SECURITY.md | Fix inaccuracies + deploy guide |

---

## 2. Launch gates (definition of done)

### L0 — Soft launch (minimum trustworthy release)

- [ ] `pip install` story works (PyPI or clear `git+...`).
- [ ] `from chatui import chat; chat()` is documented and works.
- [ ] `chat` is in `chatui/__init__.py` `__all__`.
- [ ] Auto provider from env vars.
- [ ] Per-connection `system_prompt` (no shared mutation).
- [ ] Markdown sanitized with DOMPurify; vendor libs used.
- [ ] Auth token not embedded in HTML.
- [ ] Copy-paste friendly missing-key errors everywhere.
- [ ] Real or clearly labeled demos.
- [ ] README without `YOUR_USERNAME` placeholders.
- [ ] `pytest` green on 3.9+.
- [ ] LICENSE present (MIT).

### L1 — Public beta (marketing push)

- [ ] All L0 items.
- [ ] New architecture wired: provider adapters + unified `agent_loop` replace old loops.
- [ ] `server.py` split into focused packages.
- [ ] Zed themes in a `chatui/themes/` package with canonical defaults (`ayu_light` / `one_dark`).
- [ ] Explicit layout helpers polished and documented.
- [ ] Plain `tools=[...]` API documented as primary path.
- [ ] Live public demo.
- [ ] Docker + `docker-compose.yml`.
- [ ] Deploy guide (VPS + one cloud provider).
- [ ] `lite=True` actually reduces chrome/CSS/themes.
- [ ] CORS production warning + safe examples.
- [ ] CHANGELOG maintained.
- [ ] Comparison docs vs Streamlit / Gradio / Chainlit.

### L2 — 1.0 (stable release)

- [ ] All L1 items.
- [ ] Provider Protocol stable; no duplicated loops.
- [ ] Optional durable SQLite store.
- [ ] FastAPI `mount()` / ASGI helper.
- [ ] Streaming custom reply API fully tested.
- [ ] SECURITY.md + threat model complete.
- [ ] Semver + deprecation policy written.
- [ ] WS/agent/provider test coverage solid.
- [ ] Coverage gate ≥ 70 % on core packages.

---

## 3. Critical path to launch

Do these in order. Do not start a later item until earlier items are merged and green.

### Phase A — Fix launch blockers (P0)

#### A1. Wire the new architecture

- [ ] Refactor `chatui/server.py` `_agentic_loop()` to use:
  - `chatui.providers.AnthropicProvider`
  - `chatui.providers.OpenAICompatProvider`
  - `chatui.agent.loop.agent_loop()`
- [ ] Delete `_loop_anthropic` and `_loop_openai` from `server.py`.
- [ ] Move provider client setup out of `server.py` into provider adapters.
- [ ] Update `ARCHITECTURE.md` to show the wired flow.
- [ ] Add `tests/test_agent_loop.py` with mocked provider streams.
- [ ] Add `tests/test_providers.py` for Anthropic and OpenAI-compatible adapters.

**Acceptance:**
- `server.py` no longer imports `anthropic` or `openai` directly.
- `pytest` green.
- Agent and provider modules have > 0 % coverage.

#### A2. Split `server.py`

- [ ] Create `chatui/app.py` — thin `ChatUI` orchestrator (config + registration only).
- [ ] Create `chatui/server/http.py` — `GET /`, `GET /health`.
- [ ] Create `chatui/server/ws.py` — WebSocket protocol handler.
- [ ] Create `chatui/server/middleware.py` — auth, CORS, logging, rate limit.
- [ ] Move tool/component/event registration methods to `app.py`.
- [ ] Keep public imports stable (`from chatui import ChatUI`).

**Acceptance:**
- `server.py` is gone or < 200 lines.
- `pytest` green.
- No behavior change.

#### A3. Raise test coverage

- [ ] Add mocked LLM stream tests for the unified loop.
- [ ] Add provider adapter tests.
- [ ] Add widget event round-trip tests.
- [ ] Add async/async-generator `reply` tests.
- [ ] Raise `tool.coverage.report.fail_under` from 42 to 70.

**Acceptance:**
- `pytest --cov=chatui` passes with ≥ 70 % coverage.
- No uncovered core behavior.

#### A4. Fix beginner API polish

- [ ] Add `"chat"` to `chatui/__init__.py` `__all__`.
- [ ] Replace `server.py` `_no_key_msg()` with copy-paste friendly error using `ChatUIMissingKeyError`.
- [ ] Ensure CLI missing-key message uses the same exception.

#### A5. Fix production defaults

- [ ] Add CORS warning in README and docstring.
- [ ] Change default `cors_origins` docs to recommend explicit origins in production.
- [ ] Document that `allow_credentials=True` + `["*"]` is for local dev only.
- [ ] Add `CHATUI_ENV=production` behavior:
  - `open_browser=False`
  - `lite=True` if `lite` not explicitly set
  - trimmed `/health`

### Phase B — Launch polish (P1)

#### B1. Themes package

- [ ] Move themes from `chatui/themes.py` to `chatui/themes/` package:
  - `chatui/themes/factory.py`
  - `chatui/themes/zed.py`
  - `chatui/themes/aliases.py`
  - `chatui/themes/__init__.py` (registry, labels, modes)
- [ ] Default to canonical `ayu_light` (light) and `one_dark` (dark).
- [ ] Keep old names as aliases.
- [ ] Update imports throughout codebase.
- [ ] Update tests.

#### B2. Wire `lite=True`

- [ ] When `lite=True`:
  - Ship only 2 themes to client.
  - Hide sidebar.
  - Hide import/export.
  - Serve smaller CSS (optional subset).
- [ ] Test that `lite=True` renders correctly.

#### B3. Widget polish

- [ ] Add first-run welcome chips when tools are registered.
- [ ] Add widget event round-trip tests.
- [ ] Ensure `choice`, `form`, `confirm` work end-to-end in a demo.

#### B4. Docker & deploy

- [ ] Add `Dockerfile` (slim Python image, non-root user).
- [ ] Add `docker-compose.yml` with `.env` example.
- [ ] Add deploy guide:
  - VPS with systemd or reverse proxy
  - Fly.io one-pager
  - Railway or Render one-pager
- [ ] Add reverse-proxy auth examples (Caddy/Nginx).

#### B5. Docs accuracy

- [ ] Fix README line that says `anthropic` is a core dependency.
- [ ] Rewrite README hero path around `chat()`.
- [ ] Add “From Streamlit chat” migration guide.
- [ ] Add “From Gradio ChatInterface” migration guide.
- [ ] Update `CHANGELOG.md` to remove false Docker claim or add the files.

### Phase C — 1.0 hardening (P2/P3)

#### C1. Optional durable store

- [ ] Add `ChatUI(store="sqlite")`.
- [ ] Add store path config.
- [ ] Privacy docs: what is stored where.
- [ ] Multi-worker docs with sticky sessions / Redis path.

#### C2. Mount / ASGI helper

- [ ] Add `ChatUI.asgi()` returning a FastAPI app.
- [ ] Add `app.mount("/chat", chatui_app)` example.
- [ ] Document embed/iframe mode.

#### C3. Security hardening

- [ ] Complete `SECURITY.md` threat model.
- [ ] File upload type allowlist.
- [ ] Tool allowlist / human-in-the-loop gate for `dangerous=True` tools.
- [ ] Max concurrent generations per connection.
- [ ] Structured request IDs / logging.

#### C4. Quality bar

- [ ] Semver policy written.
- [ ] Deprecation policy for theme aliases.
- [ ] Coverage gate ≥ 70 %.
- [ ] CI on 3.9 / 3.11 / 3.12 / 3.13.

---

## 4. Detailed implementation notes

### 4.1 Wiring provider adapters

Current `server.py` builds `self._client` and calls SDK streams directly. Replace with:

```python
from .providers import AnthropicProvider, OpenAICompatProvider, detect_provider_from_env
from .agent.loop import agent_loop

provider = AnthropicProvider(api_key=..., model=...)  # or OpenAICompatProvider
await agent_loop(
    provider=provider,
    registry=self._registry,
    components=self._components,
    connection=conn,
    send=send,
)
```

`agent_loop` should consume `Event` objects (`TokenEvent`, `ToolCallEvent`, etc.) and handle tool rounds, widgets, components, and stop events.

### 4.2 Splitting `server.py`

Move responsibilities:

| Current in `server.py` | New home |
|------------------------|----------|
| `ChatUI` class + registration | `chatui/app.py` |
| `GET /`, `GET /health` | `chatui/server/http.py` |
| `WebSocket /ws` handler | `chatui/server/ws.py` |
| Auth / CORS / rate limit / logging | `chatui/server/middleware.py` |
| Provider client build | `chatui/providers/` adapters |
| Agent loops | `chatui/agent/loop.py` |

### 4.3 Coverage plan

Target modules to cover:

- `chatui/agent/loop.py`
- `chatui/providers/anthropic.py`
- `chatui/providers/openai_compat.py`
- `chatui/providers/detect.py`
- `chatui/runtime/history.py` edge cases
- Async `reply` paths
- Widget event round-trip

Use mocked async iterators for provider streams.

### 4.4 `lite=True` behavior

```python
if self.lite:
    self.themes = [self.theme]  # ship only active theme
    self.show_sidebar = False
    self.allow_import_export = False
```

Server config message should include `lite: true` so the frontend can hide chrome.

### 4.5 Docker recipe

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[all]"
COPY . .
EXPOSE 8000
CMD ["python", "-m", "chatui"]
```

Add `.dockerignore`.

---

## 5. Design & quality rules (AGENTS.md)

- [ ] No pure black/white in themes.
- [ ] No purple-blue AI gradients.
- [ ] Typography roles respected.
- [ ] Ease-out motion only; respect `prefers-reduced-motion`.
- [ ] WCAG AA contrast on all themes.
- [ ] Keyboard navigation + focus rings + skip link.
- [ ] Screen reader live region for new messages.

---

## 6. PR / merge rules

- [ ] One concern per PR.
- [ ] Tests required for behavior changes.
- [ ] Update `Plan.md` checkboxes in the same PR.
- [ ] Update `ARCHITECTURE.md` when boundaries move.
- [ ] Screenshot for UI PRs (light + dark).
- [ ] No new dependency without a size/security note.
- [ ] Merge only when:
  - `pytest` green
  - Manual smoke passes (start, chat, tool, widget, theme switch, stop)
  - No secret in HTML
  - No shared mutable connection state

---

## 7. Non-goals (do not dilute)

- [ ] **Do not** add Node/Vite/Webpack build.
- [ ] **Do not** become a general multi-page Streamlit replacement.
- [ ] **Do not** break decorator API without a migration path.
- [ ] **Do not** big-bang rewrite without tests.
- [ ] **Do not** ship mock demos as production examples.
- [ ] **Do not** claim multi-worker sessions until external store exists.

---

## 8. Decision log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-07-14 | Plan created | Beginner API + Zed themes + clean split |
| 2026-07-14 | Audit found architecture not wired | Added Phase A as launch blocker |
| 2026-07-15 | Launch plan updated | Focus on wiring adapters, splitting server.py, coverage, Docker |
| | Default theme | `ayu_light` light, `one_dark` dark |
| | Coverage gate target | 70 % before L2 |
| | Docker base image | `python:3.12-slim` |

---

## 9. Task index (flat triage list)

### P0 — Must fix before any launch

- [ ] Wire provider adapters into `server.py`
- [ ] Delete `_loop_anthropic` / `_loop_openai`
- [ ] Add `tests/test_agent_loop.py`
- [ ] Add provider adapter tests
- [ ] Split `server.py` into `app.py` + `server/` package
- [ ] Add `"chat"` to `chatui/__init__.py` `__all__`
- [ ] Copy-paste friendly `_no_key_msg()`
- [ ] CORS production warning

### P1 — Public beta polish

- [ ] Move themes to `chatui/themes/` package
- [ ] Canonical default themes (`ayu_light` / `one_dark`)
- [ ] Wire `lite=True`
- [ ] First-run welcome chips
- [ ] Widget event round-trip tests
- [ ] Dockerfile + docker-compose
- [ ] Deploy guide (VPS + Fly/Railway/Render)
- [ ] Reverse-proxy auth examples
- [ ] README migration guides
- [ ] Fix README inaccuracies

### P2 — 1.0 quality

- [ ] Optional SQLite store
- [ ] FastAPI `mount()` / ASGI helper
- [ ] Human-in-the-loop for dangerous tools
- [ ] File upload allowlist
- [ ] Structured logging / request IDs
- [ ] Semver + deprecation policy

### P3 — Test & coverage

- [ ] Raise `fail_under` to 70
- [ ] Async/async-generator `reply` tests
- [ ] History edge-case tests
- [ ] Theme alias + completeness tests

### P4 — Ecosystem (after 1.0)

- [ ] Templates
- [ ] Tool packs
- [ ] Theme packs
- [ ] Plugin entry points
- [ ] Multimodal

---

*Last updated: 2026-07-15. Keep this file current as tasks land.*
