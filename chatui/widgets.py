"""
chatui/widgets.py
Interactive widgets for the chat stream.

Return widgets from tools or event handlers — they render in the browser
and send events back over WebSocket.

Example:
    from chatui import ChatUI, button, metric, progress

    app = ChatUI(provider="groq")

    @app.tool
    def show_dashboard():
        return (
            metric("Revenue", "$1.2M", delta="+12%"),
            progress(0.78, label="Project completion"),
            button("Refresh", key="refresh"),
            button("Cancel", key="cancel", variant="secondary"),
        )
"""
from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Union

_BUTTON_VARIANTS = frozenset({"primary", "secondary", "danger"})
_STATUS_STATES = frozenset({"running", "complete", "error"})
_TOAST_ICONS = frozenset({"info", "success", "warning", "error"})


class Widget:
    """A single UI element rendered in the chat stream."""

    __slots__ = ("_type", "_id", "_props")

    def __init__(self, wtype: str, **props: Any) -> None:
        self._type = wtype
        widget_id = props.pop("id", None)
        self._id = widget_id or f"w_{wtype}_{id(self):x}"
        self._props = props

    @property
    def type(self) -> str:
        return self._type

    @property
    def id(self) -> str:
        return self._id

    @property
    def props(self) -> dict:
        return self._props

    def to_payload(self) -> dict:
        return {
            "type": "widget",
            "widget": self._type,
            "id": self._id,
            "props": self._props,
        }

    def __repr__(self) -> str:
        return f"Widget({self._type!r}, id={self._id!r})"


# ── Builders ──────────────────────────────────────────────────────────────────


def button(
    label: str,
    key: str | None = None,
    variant: str = "primary",
    disabled: bool = False,
) -> Widget:
    """Clickable button. Fires ``button_click`` with ``data.key``.

    Consecutive buttons render as a shared action row in the UI.
    """
    return Widget(
        "button",
        label=label,
        key=key or label,
        variant=variant if variant in _BUTTON_VARIANTS else "primary",
        disabled=bool(disabled),
    )


def text_input(
    label: str,
    key: str,
    placeholder: str = "",
    value: str = "",
) -> Widget:
    """Text field with send action. Fires ``text_input_submit``."""
    return Widget(
        "text_input",
        label=label,
        key=key,
        placeholder=placeholder,
        value=value,
    )


def selectbox(
    label: str,
    options: Sequence[str],
    key: str,
    index: int = 0,
) -> Widget:
    """Dropdown. Fires ``selectbox_change``."""
    opts = [str(o) for o in options]
    idx = _clamp_index(index, len(opts))
    return Widget("selectbox", label=label, options=opts, key=key, index=idx)


def radio(
    label: str,
    options: Sequence[str],
    key: str,
    index: int = 0,
) -> Widget:
    """Radio group. Fires ``radio_change``."""
    opts = [str(o) for o in options]
    idx = _clamp_index(index, len(opts))
    return Widget("radio", label=label, options=opts, key=key, index=idx)


def checkbox(label: str, key: str, value: bool = False) -> Widget:
    """Checkbox. Fires ``checkbox_change``."""
    return Widget("checkbox", label=label, key=key, value=bool(value))


def slider(
    label: str,
    key: str,
    min_val: float = 0,
    max_val: float = 100,
    value: float = 50,
    step: float = 1,
) -> Widget:
    """Range slider. Fires ``slider_change``."""
    return Widget(
        "slider",
        label=label,
        key=key,
        min=float(min_val),
        max=float(max_val),
        value=float(value),
        step=float(step),
    )


def progress(value: float, label: str = "") -> Widget:
    """Progress bar. ``value`` is 0.0–1.0."""
    return Widget("progress", value=_clamp01(value), label=label)


def status(
    label: str,
    expanded: bool = False,
    state: str = "running",
) -> Widget:
    """Status row. ``state``: running | complete | error."""
    return Widget(
        "status",
        label=label,
        expanded=bool(expanded),
        state=state if state in _STATUS_STATES else "running",
    )


def table(data: Sequence[dict], caption: str = "") -> Widget:
    """Data table from a list of row dicts."""
    if not data:
        return Widget("table", columns=[], rows=[], caption=caption)
    columns = list(data[0].keys())
    rows = [[row.get(col, "") for col in columns] for row in data]
    return Widget("table", columns=columns, rows=rows, caption=caption)


def markdown(content: str) -> Widget:
    """Markdown block."""
    return Widget("markdown", content=str(content or ""))


def html(content: str) -> Widget:
    """Raw HTML (trusted content only)."""
    return Widget("html", content=str(content or ""))


def image(src: str, caption: str = "", width: int | None = None) -> Widget:
    """Image by URL or data URI."""
    props: dict[str, Any] = {"src": src, "caption": caption}
    if width is not None:
        props["width"] = int(width)
    return Widget("image", **props)


def divider() -> Widget:
    """Horizontal rule."""
    return Widget("divider")


def metric(label: str, value: Any, delta: str | None = None) -> Widget:
    """Big number with optional delta (e.g. ``+12%``).

    Consecutive metrics render as a responsive strip in the UI.
    """
    return Widget(
        "metric",
        label=label,
        value=str(value),
        delta=delta,
    )


def columns(spec: Sequence[float] | None = None) -> Widget:
    """Start a column group. Follow with widgets, then ``end_columns()``.

    Ratios map to CSS ``fr`` units (e.g. ``[2, 1]`` → ``2fr 1fr``).
    """
    ratios = list(spec) if spec else [1, 1]
    return Widget("columns", ratios=[float(r) for r in ratios])


def end_columns() -> Widget:
    """Close a column group."""
    return Widget("columns_end")


def expander(label: str, expanded: bool = False) -> Widget:
    """Start a collapsible section. Close with ``end_expander()``."""
    return Widget("expander", label=label, expanded=bool(expanded))


def end_expander() -> Widget:
    """Close an expander."""
    return Widget("expander_end")


def toast(message: str, icon: str = "info") -> Widget:
    """Transient toast. ``icon``: info | success | warning | error."""
    return Widget(
        "toast",
        message=str(message),
        icon=icon if icon in _TOAST_ICONS else "info",
    )


def file_uploader(
    label: str,
    key: str,
    accept: str | None = None,
    multiple: bool = False,
) -> Widget:
    """File drop zone. Fires ``file_upload``."""
    return Widget(
        "file_uploader",
        label=label,
        key=key,
        accept=accept or "",
        multiple=bool(multiple),
    )


def spinner(label: str = "Working on it…") -> Widget:
    """Inline spinner with status text."""
    return Widget("spinner", label=label)


# ── Internals ─────────────────────────────────────────────────────────────────


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp_index(index: int, length: int) -> int:
    if length <= 0:
        return 0
    return max(0, min(int(index), length - 1))


# ── Helpers ───────────────────────────────────────────────────────────────────


WidgetLike = Union[Widget, Sequence[Widget], None]


def collect_widgets(value: Any) -> List[Widget]:
    """
    Pull widgets out of a tool / handler return value.

    Accepts a single Widget, a list/tuple of mixed values, or nested sequences.
    """
    if value is None:
        return []
    if isinstance(value, Widget):
        return [value]
    if isinstance(value, (list, tuple)):
        out: List[Widget] = []
        for item in value:
            out.extend(collect_widgets(item))
        return out
    return []


def strip_widgets(value: Any) -> Any:
    """
    Return a JSON-friendly value for the model, without Widget objects.

    - Only widgets → {"ok": True, "ui": ["button", ...]}
    - Mix of widgets + data → data only (or list of non-widgets)
    - No widgets → value unchanged
    """
    if isinstance(value, Widget):
        return {"ok": True, "ui": [value.type]}

    if isinstance(value, (list, tuple)):
        widgets = [v for v in value if isinstance(v, Widget)]
        rest = [v for v in value if not isinstance(v, Widget)]
        if widgets and not rest:
            return {"ok": True, "ui": [w.type for w in widgets]}
        if widgets and rest:
            return rest[0] if len(rest) == 1 else list(rest)
        return list(value)

    return value


def widget_payloads(widgets: Iterable[Widget]) -> list[dict]:
    return [w.to_payload() for w in widgets]


def widget_message(*widgets: Widget) -> dict:
    """Build a widgets message dict (mostly for tests / advanced use)."""
    return {"widgets": widget_payloads(widgets)}


# ── Layout helpers (explicit, no magic grouping required) ────────────────────

import uuid


def _gen_id(prefix: str = "w") -> str:
    """Generate a stable, human-friendly widget ID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _check_unique_keys(widgets: list[Widget]) -> None:
    """Raise ValueError if any widgets have duplicate keys."""
    keys = [w.props.get("key") for w in widgets if w.props.get("key")]
    if keys and len(keys) != len(set(keys)):
        dupes = [k for k in keys if keys.count(k) > 1]
        raise ValueError(f"Duplicate widget keys: {list(set(dupes))}")


def actions(*buttons: Widget) -> Widget:
    """Explicit action row. Buttons render horizontally.

    Prefer this over relying on auto-grouping of consecutive buttons.
    """
    _check_unique_keys(list(buttons))
    return Widget("actions", id=_gen_id("actions"), children=widget_payloads(buttons))


def row(*widgets: Widget) -> Widget:
    """Horizontal group (metrics, etc.). CSS grid with equal fr units."""
    _check_unique_keys(list(widgets))
    return Widget("row", id=_gen_id("row"), children=widget_payloads(widgets))


def stack(*widgets: Widget) -> Widget:
    """Vertical stack with consistent gaps."""
    _check_unique_keys(list(widgets))
    return Widget("stack", id=_gen_id("stack"), children=widget_payloads(widgets))


def card(title: str, *children: Widget) -> Widget:
    """Single surface for mixed content.

    Avoids nested "card inside card" UI.
    """
    _check_unique_keys(list(children))
    return Widget(
        "card",
        id=_gen_id("card"),
        title=title,
        children=widget_payloads(children),
    )


# ── Chat-native widget patterns ──────────────────────────────────────────────


def choice(label: str, options: list[str], key: str) -> Widget:
    """Clickable option chips for chat flows.

    Fires ``choice_select`` with ``data.value`` = selected option.
    """
    return Widget(
        "choice",
        id=_gen_id("choice"),
        label=label,
        options=[str(o) for o in options],
        key=key,
    )


def form(*fields: Widget, submit_key: str) -> Widget:
    """Multi-field form. Returns dict of field values on submit.

    Fires ``form_submit`` with ``data.values`` = {field_key: value, ...}.
    """
    _check_unique_keys(list(fields))
    return Widget(
        "form",
        id=_gen_id("form"),
        fields=widget_payloads(fields),
        submit_key=submit_key,
    )


def confirm(message: str, yes_key: str, no_key: str) -> Widget:
    """Confirmation dialog as two buttons (actions preset)."""
    return actions(
        button(message, key=yes_key, variant="primary"),
        button("Cancel", key=no_key, variant="secondary"),
    )


__all__ = [
    "Widget",
    "button",
    "text_input",
    "selectbox",
    "radio",
    "checkbox",
    "slider",
    "progress",
    "status",
    "table",
    "markdown",
    "html",
    "image",
    "divider",
    "metric",
    "columns",
    "end_columns",
    "expander",
    "end_expander",
    "toast",
    "file_uploader",
    "spinner",
    "collect_widgets",
    "strip_widgets",
    "widget_payloads",
    "widget_message",
    "actions",
    "row",
    "stack",
    "card",
    "choice",
    "form",
    "confirm",
]
