from typing import Dict

_FONTS: Dict[str, str] = {
    "--font-sans": (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, "
        "'Helvetica Neue', Arial, sans-serif"
    ),
    "--font-mono": (
        "ui-monospace, 'SF Mono', 'Cascadia Code', 'Fira Code', Consolas, "
        "'Liberation Mono', monospace"
    ),
}

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "mode": "dark",
        "--bg-base": "oklch(13.5% 0.005 265)",
        "--bg-surface": "oklch(17.5% 0.006 265)",
        "--bg-elevated": "oklch(21.5% 0.007 265)",
        "--bg-user": "oklch(24% 0.007 265)",
        "--bg-code": "oklch(11% 0.004 265)",
        "--text-primary": "oklch(94% 0.003 265)",
        "--text-secondary": "oklch(72% 0.006 265)",
        "--text-tertiary": "oklch(52% 0.008 265)",
        "--accent": "oklch(60% 0.20 264)",
        "--accent-hover": "oklch(65% 0.19 264)",
        "--accent-ghost": "oklch(60% 0.20 264 / 0.12)",
        "--accent-fg": "oklch(99% 0.003 264)",
        "--border": "oklch(94% 0.003 265 / 0.07)",
        "--border-strong": "oklch(94% 0.003 265 / 0.14)",
        "--error": "oklch(62% 0.19 25)",
        "--success": "oklch(68% 0.14 152)",
        "--warning": "oklch(76% 0.14 85)",
        **_FONTS,
    },
    "light": {
        "mode": "light",
        "--bg-base": "oklch(99% 0.002 265)",
        "--bg-surface": "oklch(97% 0.003 265)",
        "--bg-elevated": "oklch(95% 0.004 265)",
        "--bg-user": "oklch(93% 0.005 265)",
        "--bg-code": "oklch(19% 0.006 265)",
        "--text-primary": "oklch(20% 0.006 265)",
        "--text-secondary": "oklch(42% 0.008 265)",
        "--text-tertiary": "oklch(56% 0.008 265)",
        "--accent": "oklch(50% 0.20 264)",
        "--accent-hover": "oklch(45% 0.20 264)",
        "--accent-ghost": "oklch(50% 0.20 264 / 0.10)",
        "--accent-fg": "oklch(99% 0.002 264)",
        "--border": "oklch(20% 0.006 265 / 0.08)",
        "--border-strong": "oklch(20% 0.006 265 / 0.16)",
        "--error": "oklch(50% 0.19 25)",
        "--success": "oklch(45% 0.13 152)",
        "--warning": "oklch(62% 0.14 80)",
        **_FONTS,
    },
    "sepia": {
        "mode": "light",
        "--bg-base": "oklch(97% 0.014 75)",
        "--bg-surface": "oklch(95% 0.016 72)",
        "--bg-elevated": "oklch(92% 0.020 68)",
        "--bg-user": "oklch(90% 0.022 65)",
        "--bg-code": "oklch(22% 0.012 60)",
        "--text-primary": "oklch(26% 0.020 50)",
        "--text-secondary": "oklch(44% 0.024 50)",
        "--text-tertiary": "oklch(56% 0.022 55)",
        "--accent": "oklch(54% 0.16 38)",
        "--accent-hover": "oklch(48% 0.17 38)",
        "--accent-ghost": "oklch(54% 0.16 38 / 0.12)",
        "--accent-fg": "oklch(99% 0.010 70)",
        "--border": "oklch(26% 0.020 50 / 0.10)",
        "--border-strong": "oklch(26% 0.020 50 / 0.20)",
        "--error": "oklch(50% 0.19 25)",
        "--success": "oklch(44% 0.13 150)",
        "--warning": "oklch(60% 0.14 78)",
        **_FONTS,
    },
    "slate": {
        "mode": "dark",
        "--bg-base": "oklch(14% 0.012 250)",
        "--bg-surface": "oklch(18% 0.014 250)",
        "--bg-elevated": "oklch(22% 0.016 250)",
        "--bg-user": "oklch(24% 0.018 250)",
        "--bg-code": "oklch(11% 0.010 250)",
        "--text-primary": "oklch(94% 0.006 240)",
        "--text-secondary": "oklch(72% 0.012 240)",
        "--text-tertiary": "oklch(52% 0.014 240)",
        "--accent": "oklch(72% 0.14 200)",
        "--accent-hover": "oklch(78% 0.13 200)",
        "--accent-ghost": "oklch(72% 0.14 200 / 0.12)",
        "--accent-fg": "oklch(14% 0.020 220)",
        "--border": "oklch(94% 0.006 240 / 0.07)",
        "--border-strong": "oklch(94% 0.006 240 / 0.14)",
        "--error": "oklch(65% 0.18 22)",
        "--success": "oklch(70% 0.13 155)",
        "--warning": "oklch(78% 0.13 85)",
        **_FONTS,
    },
}

THEME_LABELS: Dict[str, str] = {
    "dark": "Dark",
    "light": "Light",
    "sepia": "Sepia",
    "slate": "Slate",
}

DEFAULT_THEME = "dark"
