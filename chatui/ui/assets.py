"""
chatui/ui/assets.py
Assemble modular frontend assets (CSS) with zero build step.

CSS lives under ``chatui/ui/css/`` as ordered partials listed in
``manifest.txt``. At serve time they are concatenated into the HTML
shell — same runtime model as Streamlit (no Node, no bundler), but
the source stays maintainable.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent
CSS_DIR = UI_DIR / "css"
MANIFEST = CSS_DIR / "manifest.txt"
INDEX_HTML = UI_DIR / "index.html"


def _manifest_files() -> list[Path]:
    if MANIFEST.is_file():
        names = [
            line.strip()
            for line in MANIFEST.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return [CSS_DIR / name for name in names]
    # Fallback: alphabetical *.css
    return sorted(CSS_DIR.glob("*.css"))


@lru_cache(maxsize=1)
def load_css() -> str:
    """Return concatenated CSS for injection into the HTML shell."""
    parts: list[str] = []
    for path in _manifest_files():
        if not path.is_file():
            raise FileNotFoundError(f"CSS partial missing: {path}")
        parts.append(f"/* === {path.name} === */\n")
        parts.append(path.read_text(encoding="utf-8").rstrip())
        parts.append("\n\n")
    return "".join(parts).rstrip() + "\n"


def clear_asset_cache() -> None:
    """Drop cached CSS (useful in tests / hot-reload)."""
    load_css.cache_clear()


def load_html_shell() -> str:
    """Raw index.html template (placeholders still present)."""
    return INDEX_HTML.read_text(encoding="utf-8")


def render_html(*, theme_vars: str = "") -> str:
    """
    Build the full HTML document with CSS partials and optional theme vars.

    ``theme_vars`` should be a ``:root { ... }`` block (see themes.get_css_vars).
    """
    html = load_html_shell()
    styles = load_css()
    if theme_vars:
        styles = theme_vars.rstrip() + "\n\n" + styles
    if "/*{{STYLES}}*/" in html:
        html = html.replace("/*{{STYLES}}*/", styles)
    elif "/*{{THEME_VARS}}*/" in html:
        # Backward-compatible path if shell still has the old placeholder
        html = html.replace("/*{{THEME_VARS}}*/", theme_vars or "")
    return html
