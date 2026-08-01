"""Tests for the ChatUI server — build, routes, HTML rendering."""
from __future__ import annotations

import pytest
from chatui import ChatUI


@pytest.fixture
def echo_app() -> ChatUI:
    return ChatUI(reply=lambda m, s: f"Reply: {m}", title="Test")


class TestServerBuild:
    def test_app_created(self, echo_app: ChatUI):
        app = echo_app.app
        assert app.title == "Test"

    def test_root_returns_html(self, echo_app: ChatUI):
        from fastapi.testclient import TestClient
        client = TestClient(echo_app.app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Test" in resp.text

    def test_health_returns_ok(self, echo_app: ChatUI):
        from fastapi.testclient import TestClient
        client = TestClient(echo_app.app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_static_js_served(self, echo_app: ChatUI):
        from fastapi.testclient import TestClient
        client = TestClient(echo_app.app)
        resp = client.get("/js/app.js")
        assert resp.status_code == 200

    def test_static_vendor_served(self, echo_app: ChatUI):
        from fastapi.testclient import TestClient
        client = TestClient(echo_app.app)
        resp = client.get("/vendor/marked.min.js")
        assert resp.status_code == 200


class TestLayouts:
    def test_sidebar_layout(self):
        app = ChatUI(reply=lambda m, s: "", layout="sidebar")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "layout-sidebar" in resp.text

    def test_tabs_layout(self):
        app = ChatUI(reply=lambda m, s: "", layout="tabs")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "layout-tabs" in resp.text

    def test_invalid_layout_raises(self):
        with pytest.raises(ValueError, match="layout"):
            ChatUI(reply=lambda m, s: "", layout="invalid")


class TestThemes:
    def test_dark_theme(self):
        app = ChatUI(reply=lambda m, s: "", theme="dark")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "ACTIVE_THEME" in resp.text
        assert "THEME_DATA" in resp.text

    def test_light_theme(self):
        app = ChatUI(reply=lambda m, s: "", theme="light")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "light" in resp.text

    def test_invalid_theme_raises(self):
        with pytest.raises(ValueError, match="theme"):
            ChatUI(reply=lambda m, s: "", theme="rainbow")


class TestHTMLInjection:
    def test_title_injected(self):
        app = ChatUI(reply=lambda m, s: "", title="My Custom Bot")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "My Custom Bot" in resp.text

    def test_chips_injected(self):
        app = ChatUI(reply=lambda m, s: "", chips=["Hello", "World"])
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "Hello" in resp.text
        assert "World" in resp.text

    def test_welcome_title_injected(self):
        app = ChatUI(reply=lambda m, s: "", welcome_title="Ask me anything")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "Ask me anything" in resp.text

    def test_logo_injected(self):
        app = ChatUI(reply=lambda m, s: "", logo="*")
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        resp = client.get("/")
        assert "*" in resp.text
