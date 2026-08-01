from .palettes import THEMES, THEME_LABELS, DEFAULT_THEME

THEME_NAMES = list(THEMES.keys())


def get_css_vars(theme_name: str) -> str:
    theme = THEMES.get(theme_name) or THEMES[DEFAULT_THEME]
    lines = [f"  {key}: {value};" for key, value in theme.items() if key != "mode"]
    return ":root {\n" + "\n".join(lines) + "\n}"


def get_themes_json(subset: list[str] | None = None) -> str:
    import json
    if subset:
        themes = {name: THEMES.get(name, THEMES[DEFAULT_THEME]) for name in subset}
    else:
        themes = THEMES
    return json.dumps(themes)


__all__ = [
    "THEMES", "THEME_NAMES", "THEME_LABELS",
    "DEFAULT_THEME", "get_css_vars", "get_themes_json",
]
