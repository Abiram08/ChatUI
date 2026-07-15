"""
chatui/themes/factory.py
OKLCH theme factory — builds full token sets from hue/chroma knobs.
"""
from __future__ import annotations

from typing import Dict

_FONTS: Dict[str, str] = {
    "--font-serif": "'Cormorant Garamond', Georgia, serif",
    "--font-sans": "'Sora', system-ui, sans-serif",
    "--font-mono": "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
}

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
    is_dark = mode == "dark"
    ah = accent_hue if accent_hue is not None else hue
    ch = chroma

    if is_dark:
        bl = base_l if base_l is not None else 16.0
        al = accent_l if accent_l is not None else 72.0
        ac = accent_c if accent_c is not None else 0.13
        return {
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
        return {
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
