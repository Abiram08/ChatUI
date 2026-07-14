"""HTTP-level smoke tests for ChatUI FastAPI routes (no live LLM)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chatui import ChatUI, button, metric
from chatui.server import _RateLimiter, _html_esc


@pytest.fixture
def app():
    ui = ChatUI(
        provider="ollama",
        open_browser=False,
        port=8765,
        title="TestApp",
        logo="T",
        subtitle="Unit tests",
        chips=["Hello"],
        theme="ink",
        rate_limit=0,
        log_level="warning",
    )

    @ui.tool
    def ping(name: str = "world") -> dict:
        """Say hello."""
        return {"hello": name}

    @ui.component("badge")
    def badge(data: dict) -> str:
        return f"<span>{data.get('label', '')}</span>"

    @ui.on("button_click")
    def on_btn(data: dict):
        return {"ok": True, "key": data.get("key")}

    return ui


@pytest.fixture
def client(app):
    return TestClient(app.app)


class TestHealthAndRoot:
    def test_health(self, client, app):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["provider"] == "ollama"
        assert "ping" in body["tools"]
        assert "badge" in body["components"]
        assert body["auth"] is False

    def test_root_serves_assembled_ui(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        html = r.text
        assert "TestApp" in html
        assert ".w-btn" in html
        assert "skip-link" in html
        assert "--accent" in html
        # theme ink injected
        assert "oklch" in html

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ChatUI(provider="nope", open_browser=False)


class TestDecorators:
    def test_tool_and_component_registration(self, app):
        assert "ping" in app._registry.names()
        assert app._components.has("badge")
        assert app._components.render("badge", {"label": "X"}) == "<span>X</span>"

    def test_session_fallback(self, app):
        app.session["k"] = "v"
        assert app.session["k"] == "v"

    def test_tool_execute_via_registry(self, app):
        out = app._registry.execute("ping", {"name": "ada"})
        assert out == {"hello": "ada"}


class TestHelpers:
    def test_html_esc(self):
        assert _html_esc('<script>"x"&') == "&lt;script&gt;&quot;x&quot;&amp;"

    def test_rate_limiter(self):
        lim = _RateLimiter(max_requests=2, window=60.0)
        assert lim.check("a") is True
        assert lim.check("a") is True
        assert lim.check("a") is False
        assert lim.check("b") is True


class TestWidgetsWithApp:
    def test_widgets_still_collectable(self):
        widgets = [button("Go"), metric("N", 1)]
        from chatui.widgets import collect_widgets, strip_widgets

        assert len(collect_widgets(widgets)) == 2
        assert strip_widgets(widgets)["ok"] is True
