"""
chatui/themes.py
Perceptually uniform themes built on OKLCH.

Design rules (AGENTS.md):
- Tinted neutrals only — never pure black/white
- One dominant accent per theme (~60% of colored UI)
- Semantic colors for state only
- WCAG AA contrast for body text and UI controls
"""
from __future__ import annotations

import json
from typing import Dict, Mapping

# Shared typefaces — every theme inherits these
_FONTS: Dict[str, str] = {
    "--font-serif": "'Cormorant Garamond', Georgia, serif",
    "--font-sans": "'Sora', system-ui, sans-serif",
    "--font-mono": "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
}

# Semantic state colors (not brand accents)
_SEMANTIC_LIGHT: Dict[str, str] = {
    "--error": "oklch(52% 0.18 25)",
    "--success": "oklch(48% 0.13 150)",
    "--warning": "oklch(62% 0.14 75)",
}

_SEMANTIC_DARK: Dict[str, str] = {
    "--error": "oklch(68% 0.17 25)",
    "--success": "oklch(72% 0.13 155)",
    "--warning": "oklch(78% 0.13 85)",
}


def _theme(
    mode: str,
    *,
    hue: float,
    accent_hue: float | None = None,
    accent_l: float | None = None,
    accent_c: float | None = None,
    base_l: float | None = None,
    chroma: float = 0.012,
) -> Dict[str, str]:
    """
    Build a full token set from a few hue/chroma knobs.

    Light themes sit near paper (~97% L). Dark themes sit near ink (~16% L).
    Accent gets its own hue so brand color can diverge from neutral tint.
    """
    is_dark = mode == "dark"
    ah = accent_hue if accent_hue is not None else hue
    ch = chroma

    if is_dark:
        bl = base_l if base_l is not None else 16.0
        al = accent_l if accent_l is not None else 72.0
        ac = accent_c if accent_c is not None else 0.13
        tokens = {
            "mode": mode,
            "--bg-base": f"oklch({bl:.1f}% {ch:.3f} {hue})",
            "--bg-surface": f"oklch({bl + 5:.1f}% {ch + 0.003:.3f} {hue})",
            "--bg-elevated": f"oklch({bl + 10:.1f}% {ch + 0.006:.3f} {hue})",
            "--bg-user": f"oklch({bl + 9:.1f}% {ch + 0.008:.3f} {ah})",
            "--bg-code": f"oklch({max(bl - 4, 10):.1f}% {ch:.3f} {hue})",
            "--text-primary": f"oklch(93% 0.012 {hue})",
            "--text-secondary": f"oklch(72% 0.018 {hue})",
            "--text-tertiary": f"oklch(58% 0.016 {hue})",
            "--accent": f"oklch({al:.0f}% {ac:.2f} {ah})",
            "--accent-hover": f"oklch({min(al + 6, 86):.0f}% {min(ac + 0.01, 0.22):.2f} {ah})",
            "--accent-ghost": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.12)",
            "--accent-glow": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.24)",
            "--accent-fg": f"oklch({bl + 2:.1f}% {ch:.3f} {hue})",
            "--border": f"oklch(93% 0.01 {hue} / 0.11)",
            "--border-strong": f"oklch(93% 0.01 {hue} / 0.20)",
            "--border-focus": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.55)",
            "--tool-text": f"oklch(74% 0.11 160)",
            "--tool-bg": f"oklch(74% 0.11 160 / 0.09)",
            "--tool-border": f"oklch(74% 0.11 160 / 0.24)",
            **_SEMANTIC_DARK,
            **_FONTS,
        }
    else:
        bl = base_l if base_l is not None else 97.0
        al = accent_l if accent_l is not None else 48.0
        ac = accent_c if accent_c is not None else 0.14
        tokens = {
            "mode": mode,
            "--bg-base": f"oklch({bl:.1f}% {ch:.3f} {hue})",
            "--bg-surface": f"oklch({min(bl + 1.5, 99.2):.1f}% {max(ch - 0.004, 0.004):.3f} {hue})",
            "--bg-elevated": f"oklch({bl - 2.5:.1f}% {ch + 0.004:.3f} {hue})",
            "--bg-user": f"oklch({bl - 5:.1f}% {ch + 0.01:.3f} {ah})",
            "--bg-code": f"oklch(22% {ch + 0.005:.3f} {hue})",
            "--text-primary": f"oklch(22% 0.018 {hue})",
            "--text-secondary": f"oklch(42% 0.022 {hue})",
            "--text-tertiary": f"oklch(52% 0.018 {hue})",
            "--accent": f"oklch({al:.0f}% {ac:.2f} {ah})",
            "--accent-hover": f"oklch({max(al - 6, 32):.0f}% {min(ac + 0.01, 0.20):.2f} {ah})",
            "--accent-ghost": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.09)",
            "--accent-glow": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.18)",
            "--accent-fg": f"oklch({min(bl + 1.5, 99.2):.1f}% {max(ch - 0.004, 0.004):.3f} {hue})",
            "--border": f"oklch(22% 0.018 {hue} / 0.11)",
            "--border-strong": f"oklch(22% 0.018 {hue} / 0.20)",
            "--border-focus": f"oklch({al:.0f}% {ac:.2f} {ah} / 0.50)",
            "--tool-text": f"oklch(42% 0.11 155)",
            "--tool-bg": f"oklch(48% 0.11 155 / 0.07)",
            "--tool-border": f"oklch(42% 0.11 155 / 0.22)",
            **_SEMANTIC_LIGHT,
            **_FONTS,
        }
    return tokens


THEMES: Mapping[str, Dict[str, str]] = {
    # Warm paper · espresso type · terracotta accent
    "manuscript": _theme(
        "light",
        hue=70,
        accent_hue=42,
        accent_l=50,
        accent_c=0.14,
        base_l=97.2,
        chroma=0.014,
    ),
    # Cool salt-white · deep teal
    "atoll": _theme(
        "light",
        hue=220,
        accent_hue=200,
        accent_l=46,
        accent_c=0.11,
        base_l=97.0,
        chroma=0.012,
    ),
    # Soft beige · olive
    "grain": _theme(
        "light",
        hue=95,
        accent_hue=125,
        accent_l=44,
        accent_c=0.11,
        base_l=95.5,
        chroma=0.018,
    ),
    # Blush · rose
    "rose": _theme(
        "light",
        hue=12,
        accent_hue=12,
        accent_l=50,
        accent_c=0.14,
        base_l=97.0,
        chroma=0.014,
    ),
    # Fresh mint · crisp green
    "mint": _theme(
        "light",
        hue=155,
        accent_hue=158,
        accent_l=44,
        accent_c=0.13,
        base_l=97.0,
        chroma=0.016,
    ),
    # Near-black · warm amber
    "ink": _theme(
        "dark",
        hue=65,
        accent_hue=75,
        accent_l=74,
        accent_c=0.13,
        base_l=15.5,
        chroma=0.012,
    ),
    # Graphite · coral
    "obsidian": _theme(
        "dark",
        hue=40,
        accent_hue=28,
        accent_l=70,
        accent_c=0.15,
        base_l=16.0,
        chroma=0.010,
    ),
    # Deep navy · soft periwinkle (not electric purple)
    "nocturne": _theme(
        "dark",
        hue=255,
        accent_hue=250,
        accent_l=74,
        accent_c=0.10,
        base_l=17.0,
        chroma=0.028,
    ),
    # Charcoal slate · indigo (replaces neon violet “AI slop”)
    "midnight": _theme(
        "dark",
        hue=265,
        accent_hue=255,
        accent_l=72,
        accent_c=0.11,
        base_l=14.5,
        chroma=0.022,
    ),
}

THEME_NAMES = list(THEMES.keys())

THEME_LABELS = {
    "manuscript": "Manuscript",
    "atoll": "Atoll",
    "grain": "Grain",
    "ink": "Ink",
    "obsidian": "Obsidian",
    "nocturne": "Nocturne",
    "rose": "Rose",
    "mint": "Mint",
    "midnight": "Midnight",
}

THEME_MODES = {
    "light": ["manuscript", "atoll", "grain", "rose", "mint"],
    "dark": ["ink", "obsidian", "nocturne", "midnight"],
}

DEFAULT_THEME = "manuscript"


def get_css_vars(theme_name: str) -> str:
    """Return a ``:root { ... }`` block for the given theme name."""
    theme = THEMES.get(theme_name) or THEMES[DEFAULT_THEME]
    lines = [f"  {key}: {value};" for key, value in theme.items() if key != "mode"]
    return ":root {\n" + "\n".join(lines) + "\n}"


def get_themes_json() -> str:
    """Return all theme data as JSON for client-side theme switching."""
    return json.dumps(THEMES)
