"""
chatui/themes.py
7 hand-crafted dark themes for ChatUI.
"""

THEMES = {

    # ── The Dark Side — imperial cold, pure black, icy steel ──────────
    "darkside": {
        "--bg-base":        "#000000",
        "--bg-surface":     "#0a0a0f",
        "--bg-elevated":    "#0f0f1a",
        "--bg-user-msg":    "#0d0d2e",
        "--border-subtle":  "#13131f",
        "--border-medium":  "#1c1c33",
        "--border-focus":   "#3b3b6b",
        "--text-primary":   "#c8cdd8",
        "--text-secondary": "#6b7385",
        "--text-tertiary":  "#2e3245",
        "--text-accent":    "#8892b0",
        "--accent":         "#4a4e6b",
        "--accent-hover":   "#5c6180",
        "--accent-glow":    "rgba(74,78,107,0.20)",
        "--tool-border":    "rgba(139,148,176,0.20)",
        "--tool-bg":        "rgba(139,148,176,0.04)",
        "--tool-text":      "#8892b0",
        "--tool-arg":       "#3a3f52",
        "--tool-result":    "#6b7385",
        "--error":          "#9e3d3d",
        "--success":        "#2d6b4a",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Tokyo Night — neon city at 3am, electric blue + cyan ──────────
    "tokyonight": {
        "--bg-base":        "#1a1b26",
        "--bg-surface":     "#16161e",
        "--bg-elevated":    "#1f2335",
        "--bg-user-msg":    "#1e2050",
        "--border-subtle":  "#1f2335",
        "--border-medium":  "#292e42",
        "--border-focus":   "#7aa2f7",
        "--text-primary":   "#c0caf5",
        "--text-secondary": "#565f89",
        "--text-tertiary":  "#3b4261",
        "--text-accent":    "#7aa2f7",
        "--accent":         "#7aa2f7",
        "--accent-hover":   "#89b4ff",
        "--accent-glow":    "rgba(122,162,247,0.15)",
        "--tool-border":    "rgba(115,218,202,0.25)",
        "--tool-bg":        "rgba(115,218,202,0.05)",
        "--tool-text":      "#73daca",
        "--tool-arg":       "#3b4261",
        "--tool-result":    "#7aa2f7",
        "--error":          "#f7768e",
        "--success":        "#9ece6a",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Rosé Pine — deep plum, dusty rose, soft lavender ──────────────
    "rosepine": {
        "--bg-base":        "#191724",
        "--bg-surface":     "#1f1d2e",
        "--bg-elevated":    "#26233a",
        "--bg-user-msg":    "#2a1f3d",
        "--border-subtle":  "#26233a",
        "--border-medium":  "#403d52",
        "--border-focus":   "#c4a7e7",
        "--text-primary":   "#e0def4",
        "--text-secondary": "#908caa",
        "--text-tertiary":  "#6e6a86",
        "--text-accent":    "#c4a7e7",
        "--accent":         "#ebbcba",
        "--accent-hover":   "#f2c1be",
        "--accent-glow":    "rgba(235,188,186,0.15)",
        "--tool-border":    "rgba(235,188,186,0.25)",
        "--tool-bg":        "rgba(235,188,186,0.05)",
        "--tool-text":      "#ebbcba",
        "--tool-arg":       "#6e6a86",
        "--tool-result":    "#c4a7e7",
        "--error":          "#eb6f92",
        "--success":        "#31748f",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Gruvbox — retro warm, cream text, orange soul, earthy tones ───
    "gruvbox": {
        "--bg-base":        "#1d2021",
        "--bg-surface":     "#282828",
        "--bg-elevated":    "#32302f",
        "--bg-user-msg":    "#3c3836",
        "--border-subtle":  "#32302f",
        "--border-medium":  "#504945",
        "--border-focus":   "#d79921",
        "--text-primary":   "#ebdbb2",
        "--text-secondary": "#a89984",
        "--text-tertiary":  "#665c54",
        "--text-accent":    "#d79921",
        "--accent":         "#d65d0e",
        "--accent-hover":   "#fe8019",
        "--accent-glow":    "rgba(214,93,14,0.15)",
        "--tool-border":    "rgba(184,187,38,0.25)",
        "--tool-bg":        "rgba(184,187,38,0.05)",
        "--tool-text":      "#b8bb26",
        "--tool-arg":       "#665c54",
        "--tool-result":    "#d79921",
        "--error":          "#cc241d",
        "--success":        "#98971a",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Catppuccin Mocha — soft pastel dark, mauve + peach + green ────
    "catppuccin": {
        "--bg-base":        "#1e1e2e",
        "--bg-surface":     "#181825",
        "--bg-elevated":    "#313244",
        "--bg-user-msg":    "#2a2a3e",
        "--border-subtle":  "#313244",
        "--border-medium":  "#45475a",
        "--border-focus":   "#cba6f7",
        "--text-primary":   "#cdd6f4",
        "--text-secondary": "#a6adc8",
        "--text-tertiary":  "#6c7086",
        "--text-accent":    "#cba6f7",
        "--accent":         "#cba6f7",
        "--accent-hover":   "#d4b8ff",
        "--accent-glow":    "rgba(203,166,247,0.15)",
        "--tool-border":    "rgba(166,227,161,0.25)",
        "--tool-bg":        "rgba(166,227,161,0.05)",
        "--tool-text":      "#a6e3a1",
        "--tool-arg":       "#6c7086",
        "--tool-result":    "#f5c2e7",
        "--error":          "#f38ba8",
        "--success":        "#a6e3a1",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Nord — arctic minimal, four polar shades, aurora accents ──────
    "nord": {
        "--bg-base":        "#2e3440",
        "--bg-surface":     "#3b4252",
        "--bg-elevated":    "#434c5e",
        "--bg-user-msg":    "#2e3f5c",
        "--border-subtle":  "#3b4252",
        "--border-medium":  "#434c5e",
        "--border-focus":   "#88c0d0",
        "--text-primary":   "#eceff4",
        "--text-secondary": "#9aa0ad",
        "--text-tertiary":  "#616a7a",
        "--text-accent":    "#88c0d0",
        "--accent":         "#5e81ac",
        "--accent-hover":   "#81a1c1",
        "--accent-glow":    "rgba(136,192,208,0.15)",
        "--tool-border":    "rgba(163,190,140,0.25)",
        "--tool-bg":        "rgba(163,190,140,0.05)",
        "--tool-text":      "#a3be8c",
        "--tool-arg":       "#616a7a",
        "--tool-result":    "#88c0d0",
        "--error":          "#bf616a",
        "--success":        "#a3be8c",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },

    # ── Ayu Dark — ink black, fire orange, amber, teal tools ──────────
    "ayu": {
        "--bg-base":        "#0d0e0f",
        "--bg-surface":     "#131721",
        "--bg-elevated":    "#1a1f2e",
        "--bg-user-msg":    "#1c1f0f",
        "--border-subtle":  "#151a20",
        "--border-medium":  "#1f2430",
        "--border-focus":   "#ffb454",
        "--text-primary":   "#bfbdb6",
        "--text-secondary": "#5c6773",
        "--text-tertiary":  "#3d4751",
        "--text-accent":    "#ffb454",
        "--accent":         "#ff8f40",
        "--accent-hover":   "#ffb454",
        "--accent-glow":    "rgba(255,143,64,0.15)",
        "--tool-border":    "rgba(95,180,180,0.25)",
        "--tool-bg":        "rgba(95,180,180,0.05)",
        "--tool-text":      "#5fb4b4",
        "--tool-arg":       "#3d4751",
        "--tool-result":    "#ffb454",
        "--error":          "#ff3333",
        "--success":        "#91b362",
        "--font-sans":      "'Inter', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Fira Code', monospace",
    },
}

THEME_NAMES = list(THEMES.keys())


def get_css_vars(theme_name: str) -> str:
    """Return a :root { ... } block for the given theme name."""
    theme = THEMES.get(theme_name, THEMES["tokyonight"])
    lines = ["  " + k + ": " + v + ";" for k, v in theme.items()]
    return ":root {\n" + "\n".join(lines) + "\n}"


def get_themes_json() -> str:
    """Return all theme data as JSON for client-side theme switching."""
    import json
    return json.dumps(THEMES)
