"""
chatui/themes/__init__.py
Theme registry — public API for theme lookup, CSS generation, and JSON export.
"""
from __future__ import annotations

import json
from typing import Dict

from .factory import _theme
from .zed import ZED_THEMES
from .aliases import LEGACY_THEMES, ALIASES

# Combined theme registry
THEMES: Dict[str, Dict[str, str]] = {}
THEMES.update(ZED_THEMES)
for name, tokens in LEGACY_THEMES.items():
    if name not in THEMES:
        THEMES[name] = tokens

THEME_NAMES = list(THEMES.keys())

THEME_LABELS: Dict[str, str] = {
    "one_dark": "One Dark",
    "zed_dark": "Zed Dark",
    "zed_light": "Zed Light",
    "ayu_dark": "Ayu Dark",
    "ayu_light": "Ayu Light",
    "rose_pine": "Rose Pine",
    "rose_pine_dawn": "Rose Pine Dawn",
    "catppuccin_mocha": "Catppuccin Mocha",
    "catppuccin_latte": "Catppuccin Latte",
    "gruvbox_dark": "Gruvbox Dark",
    "solarized_light": "Solarized Light",
    "manuscript": "Manuscript",
    "atoll": "Atoll",
    "grain": "Grain",
    "rose": "Rose",
    "mint": "Mint",
    "ink": "Ink",
    "obsidian": "Obsidian",
    "nocturne": "Nocturne",
    "midnight": "Midnight",
}

THEME_MODES: Dict[str, list[str]] = {
    "dark": [n for n, t in THEMES.items() if t.get("mode") == "dark"],
    "light": [n for n, t in THEMES.items() if t.get("mode") == "light"],
}

DEFAULT_THEME = "manuscript"


def _resolve_theme(name: str) -> str:
    """Resolve theme name, following aliases."""
    if name in ALIASES and name not in ZED_THEMES:
        return ALIASES[name]
    return name


def get_css_vars(theme_name: str) -> str:
    """Return a :root { ... } block for the given theme name."""
    resolved = _resolve_theme(theme_name)
    fallback = _resolve_theme(DEFAULT_THEME)
    theme = THEMES.get(resolved) or THEMES.get(theme_name) or THEMES.get(fallback) or THEMES[DEFAULT_THEME]
    lines = [f"  {key}: {value};" for key, value in theme.items() if key != "mode"]
    return ":root {\n" + "\n".join(lines) + "\n}"


def get_themes_json(subset: list[str] | None = None) -> str:
    """Return theme data as JSON for client-side theme switching."""
    if subset:
        themes = {name: THEMES.get(name, THEMES[DEFAULT_THEME]) for name in subset}
    else:
        themes = THEMES
    return json.dumps(themes)


__all__ = [
    "THEMES",
    "THEME_NAMES",
    "THEME_LABELS",
    "THEME_MODES",
    "DEFAULT_THEME",
    "get_css_vars",
    "get_themes_json",
]
