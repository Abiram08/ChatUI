"""Unit tests for chatui.themes — palettes, CSS vars, JSON export."""
from __future__ import annotations

import json

import pytest

from chatui.themes import (
    DEFAULT_THEME,
    THEME_LABELS,
    THEME_MODES,
    THEME_NAMES,
    THEMES,
    get_css_vars,
    get_themes_json,
)

REQUIRED_TOKENS = {
    "--bg-base",
    "--bg-surface",
    "--bg-elevated",
    "--bg-user",
    "--bg-code",
    "--text-primary",
    "--text-secondary",
    "--text-tertiary",
    "--accent",
    "--accent-hover",
    "--accent-ghost",
    "--accent-glow",
    "--accent-fg",
    "--border",
    "--border-strong",
    "--border-focus",
    "--error",
    "--success",
    "--warning",
    "--font-serif",
    "--font-sans",
    "--font-mono",
}

FORBIDDEN_COLORS = {
    "#000",
    "#000000",
    "#fff",
    "#ffffff",
    "white",
    "black",
    "oklch(100% 0 0)",
    "oklch(0% 0 0)",
}


class TestThemeCatalog:
    def test_theme_count(self):
        # 11 Zed-inspired + 9 legacy = 20 themes
        assert len(THEMES) == 20
        assert len(THEME_NAMES) == 20

    def test_zed_themes_present(self):
        for name in ("one_dark", "zed_dark", "ayu_light", "rose_pine", "catppuccin_mocha"):
            assert name in THEMES, f"{name} missing"

    def test_legacy_themes_present(self):
        for name in ("manuscript", "ink", "obsidian", "midnight"):
            assert name in THEMES, f"{name} missing"

    def test_default_exists(self):
        assert DEFAULT_THEME in THEMES

    def test_labels_cover_all(self):
        assert set(THEME_LABELS) == set(THEMES)

    def test_modes_partition(self):
        light = set(THEME_MODES["light"])
        dark = set(THEME_MODES["dark"])
        assert light.isdisjoint(dark)
        assert light | dark == set(THEMES)

    def test_each_theme_has_required_tokens(self):
        for name, theme in THEMES.items():
            assert theme["mode"] in ("light", "dark"), name
            missing = REQUIRED_TOKENS - set(theme)
            assert not missing, f"{name} missing {missing}"

    def test_no_pure_black_or_white(self):
        for name, theme in THEMES.items():
            for key, value in theme.items():
                if key == "mode":
                    continue
                assert value not in FORBIDDEN_COLORS, f"{name}.{key}={value}"
                # surfaces should carry chroma (tinted neutrals)
                if key.startswith("--bg-") and "oklch" in value:
                    assert "oklch(100%" not in value, name


class TestCssExport:
    def test_get_css_vars_shape(self):
        css = get_css_vars("manuscript")
        assert css.startswith(":root {")
        assert css.endswith("}")
        assert "--accent:" in css
        assert "--accent-fg:" in css
        assert "mode" not in css.split(":")[0]  # mode not as bare property

    def test_unknown_theme_falls_back(self):
        css = get_css_vars("does-not-exist")
        assert "--accent:" in css
        # same as default
        assert get_css_vars(DEFAULT_THEME) == css

    def test_themes_json_roundtrip(self):
        data = json.loads(get_themes_json())
        assert set(data) == set(THEMES)
        assert data["ink"]["mode"] == "dark"
        assert "--accent-fg" in data["ink"]

    @pytest.mark.parametrize("name", THEME_NAMES)
    def test_oklch_tokens(self, name):
        theme = THEMES[name]
        for key, value in theme.items():
            if key in ("mode",) or key.startswith("--font-"):
                continue
            assert "oklch(" in value or value.startswith("oklch"), f"{name}.{key}"
