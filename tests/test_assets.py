"""Unit tests for modular UI asset assembly."""
from __future__ import annotations

from pathlib import Path

import pytest

from chatui.themes import get_css_vars
from chatui.ui.assets import (
    CSS_DIR,
    clear_asset_cache,
    load_css,
    load_html_shell,
    render_html,
)


@pytest.fixture(autouse=True)
def _clear_css_cache():
    clear_asset_cache()
    yield
    clear_asset_cache()


class TestCssPartials:
    def test_manifest_files_exist(self):
        manifest = (CSS_DIR / "manifest.txt").read_text(encoding="utf-8")
        names = [ln.strip() for ln in manifest.splitlines() if ln.strip()]
        assert names[0].startswith("00-")
        for name in names:
            assert (CSS_DIR / name).is_file(), name

    def test_load_css_includes_tokens_and_widgets(self):
        css = load_css()
        assert "--space-1" in css
        assert ".w-btn" in css
        assert ".skip-link" in css
        assert "/* === 00-tokens.css === */" in css
        assert "/* === 05-widgets.css === */" in css

    def test_load_css_cached(self):
        a = load_css()
        b = load_css()
        assert a is b  # lru_cache returns same object


class TestHtmlRender:
    def test_shell_has_placeholder(self):
        shell = load_html_shell()
        assert "/*{{STYLES}}*/" in shell
        assert "{{TITLE}}" in shell

    def test_render_injects_styles_and_theme(self):
        html = render_html(theme_vars=get_css_vars("atoll"))
        assert "/*{{STYLES}}*/" not in html
        assert "--accent:" in html
        assert ".w-actions" in html
        assert 'class="skip-link"' in html
        assert 'role="log"' in html

    def test_render_without_theme_still_works(self):
        html = render_html()
        assert ".app" in html
        assert len(html) > 10_000
