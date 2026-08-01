"""Tests for the frontend asset assembly."""
from __future__ import annotations

from chatui.ui.assets import load_css, render_html, clear_asset_cache, load_html_shell


class TestCSSLoading:
    def setup_method(self):
        clear_asset_cache()

    def test_load_css_returns_string(self):
        css = load_css()
        assert isinstance(css, str)
        assert len(css) > 100

    def test_load_css_contains_base_styles(self):
        css = load_css()
        assert "--font-sans" in css
        assert "--bg-base" in css

    def test_load_css_contains_layout_styles(self):
        css = load_css()
        assert ".sidebar" in css
        assert ".composer" in css

    def test_load_css_caches(self):
        css1 = load_css()
        css2 = load_css()
        assert css1 is css2

    def test_clear_cache(self):
        css1 = load_css()
        clear_asset_cache()
        css2 = load_css()
        assert css1 is not css2


class TestHTMLShell:
    def test_shell_has_placeholders(self):
        html = load_html_shell()
        assert "{{TITLE}}" in html
        assert "{{LAYOUT}}" in html
        assert "{{THEMES_JSON}}" in html
        assert "{{ACTIVE_THEME}}" in html
        assert "{{CHIPS_JSON}}" in html
        assert "{{WELCOME_TITLE}}" in html
        assert "{{SUBTITLE}}" in html
        assert "{{LOGO}}" in html
        assert "/*{{STYLES}}*/" in html

    def test_shell_has_required_elements(self):
        html = load_html_shell()
        assert "sidebar" in html
        assert "composer" in html
        assert "messageList" in html
        assert "settingsPanel" in html
        assert "themeSelect" in html
        assert "chatHeader" in html
        assert "scrollBtn" in html
        assert "statusDot" in html
        assert "toastContainer" in html


class TestRenderHTML:
    def test_render_replaces_style_placeholder(self):
        html = render_html(theme_vars=":root { --test: red; }")
        assert "/*{{STYLES}}*/" not in html

    def test_render_includes_theme_vars(self):
        html = render_html(theme_vars=":root { --test: red; }")
        assert "--test: red" in html

    def test_render_without_theme_vars(self):
        html = render_html()
        assert "/*{{STYLES}}*/" not in html
