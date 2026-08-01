"""Tests for the theme system — palette definitions and CSS generation."""
from __future__ import annotations

from chatui.themes import (
    THEMES,
    THEME_NAMES,
    THEME_LABELS,
    DEFAULT_THEME,
    get_css_vars,
    get_themes_json,
)


class TestThemeData:
    def test_has_four_themes(self):
        assert len(THEMES) == 4

    def test_all_themes_in_names(self):
        for name in ("dark", "light", "sepia", "slate"):
            assert name in THEME_NAMES

    def test_all_themes_have_labels(self):
        for name in THEME_NAMES:
            assert name in THEME_LABELS

    def test_default_is_dark(self):
        assert DEFAULT_THEME == "dark"

    def test_each_theme_has_required_keys(self):
        required = {"mode", "--bg-base", "--text-primary", "--accent"}
        for name, theme in THEMES.items():
            assert required.issubset(theme.keys()), f"{name} missing keys"

    def test_each_theme_has_fonts(self):
        for name, theme in THEMES.items():
            assert "--font-sans" in theme
            assert "--font-mono" in theme

    def test_each_theme_has_mode(self):
        for name, theme in THEMES.items():
            assert theme["mode"] in ("dark", "light")


class TestCSSVars:
    def test_get_css_vars_returns_root_block(self):
        css = get_css_vars("dark")
        assert css.startswith(":root {")
        assert css.endswith("}")
        assert "--bg-base" in css
        assert "--accent" in css

    def test_get_css_vars_fallback_to_default(self):
        css = get_css_vars("nonexistent")
        assert "--bg-base" in css

    def test_get_css_vars_excludes_mode(self):
        css = get_css_vars("light")
        assert "mode" not in css

    def test_all_themes_generate_valid_css(self):
        for name in THEME_NAMES:
            css = get_css_vars(name)
            assert css.startswith(":root {")
            assert css.count("--") >= 15


class TestThemesJSON:
    def test_returns_valid_json(self):
        import json
        data = json.loads(get_themes_json())
        assert isinstance(data, dict)
        assert len(data) == 4

    def test_subset_filter(self):
        import json
        data = json.loads(get_themes_json(subset=["dark", "light"]))
        assert set(data.keys()) == {"dark", "light"}

    def test_subset_with_default(self):
        import json
        data = json.loads(get_themes_json(subset=["nonexistent"]))
        assert "nonexistent" in data

    def test_values_contain_css_vars(self):
        import json
        data = json.loads(get_themes_json())
        for name, theme in data.items():
            assert "--bg-base" in theme
