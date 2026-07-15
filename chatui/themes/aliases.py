"""
chatui/themes/aliases.py
Legacy theme names -> new Zed-inspired names.
"""
from __future__ import annotations

from typing import Dict
from .factory import _theme

LEGACY_THEMES: Dict[str, Dict[str, str]] = {
    "manuscript": _theme("light", hue=70, accent_hue=42, accent_l=50, accent_c=0.14, base_l=97.2, chroma=0.014),
    "atoll": _theme("light", hue=220, accent_hue=200, accent_l=46, accent_c=0.11, base_l=97.0, chroma=0.012),
    "grain": _theme("light", hue=95, accent_hue=125, accent_l=44, accent_c=0.11, base_l=95.5, chroma=0.018),
    "rose": _theme("light", hue=12, accent_hue=12, accent_l=50, accent_c=0.14, base_l=97.0, chroma=0.014),
    "mint": _theme("light", hue=155, accent_hue=158, accent_l=44, accent_c=0.13, base_l=97.0, chroma=0.016),
    "ink": _theme("dark", hue=65, accent_hue=75, accent_l=74, accent_c=0.13, base_l=15.5, chroma=0.012),
    "obsidian": _theme("dark", hue=40, accent_hue=28, accent_l=70, accent_c=0.15, base_l=16.0, chroma=0.010),
    "nocturne": _theme("dark", hue=255, accent_hue=250, accent_l=74, accent_c=0.10, base_l=17.0, chroma=0.028),
    "midnight": _theme("dark", hue=265, accent_hue=255, accent_l=72, accent_c=0.11, base_l=14.5, chroma=0.022),
}

ALIASES: Dict[str, str] = {
    "manuscript": "ayu_light",
    "atoll": "zed_light",
    "grain": "solarized_light",
    "rose": "rose_pine_dawn",
    "mint": "catppuccin_latte",
    "ink": "one_dark",
    "obsidian": "zed_dark",
    "nocturne": "ayu_dark",
    "midnight": "rose_pine",
}
