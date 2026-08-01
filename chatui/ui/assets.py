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
    return sorted(CSS_DIR.glob("*.css"))


@lru_cache(maxsize=1)
def load_css() -> str:
    parts: list[str] = []
    for path in _manifest_files():
        if not path.is_file():
            raise FileNotFoundError(f"CSS partial missing: {path}")
        parts.append(path.read_text(encoding="utf-8").rstrip())
        parts.append("\n\n")
    return "".join(parts).rstrip() + "\n"


def clear_asset_cache() -> None:
    load_css.cache_clear()


def load_html_shell() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def render_html(*, theme_vars: str = "") -> str:
    html = load_html_shell()
    styles = load_css()
    if theme_vars:
        styles = theme_vars.rstrip() + "\n\n" + styles
    html = html.replace("/*{{STYLES}}*/", styles)
    return html
