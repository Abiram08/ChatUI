"""
chatui/themes/zed.py
Zed/editor-inspired theme palettes.
"""
from __future__ import annotations

from typing import Dict
from .factory import _theme

ZED_THEMES: Dict[str, Dict[str, str]] = {
    "one_dark": _theme("dark", hue=220, accent_hue=210, accent_l=72, accent_c=0.14, base_l=16.0, chroma=0.010),
    "zed_dark": _theme("dark", hue=240, accent_hue=220, accent_l=70, accent_c=0.10, base_l=16.5, chroma=0.008),
    "zed_light": _theme("light", hue=220, accent_hue=210, accent_l=48, accent_c=0.11, base_l=97.0, chroma=0.008),
    "ayu_dark": _theme("dark", hue=30, accent_hue=35, accent_l=72, accent_c=0.12, base_l=16.0, chroma=0.014),
    "ayu_light": _theme("light", hue=40, accent_hue=35, accent_l=50, accent_c=0.12, base_l=97.5, chroma=0.010),
    "rose_pine": _theme("dark", hue=350, accent_hue=350, accent_l=68, accent_c=0.12, base_l=17.0, chroma=0.016),
    "rose_pine_dawn": _theme("light", hue=40, accent_hue=350, accent_l=50, accent_c=0.13, base_l=97.0, chroma=0.012),
    "catppuccin_mocha": _theme("dark", hue=280, accent_hue=210, accent_l=72, accent_c=0.13, base_l=17.0, chroma=0.014),
    "catppuccin_latte": _theme("light", hue=280, accent_hue=210, accent_l=48, accent_c=0.12, base_l=97.5, chroma=0.010),
    "gruvbox_dark": _theme("dark", hue=55, accent_hue=40, accent_l=70, accent_c=0.15, base_l=16.0, chroma=0.016),
    "solarized_light": _theme("light", hue=55, accent_hue=25, accent_l=50, accent_c=0.13, base_l=97.0, chroma=0.012),
}
