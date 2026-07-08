"""
chatui/widgets.py
Interactive widget builder — send buttons, forms, progress bars, status containers,
tables, and more from Python that render natively in the chat UI.

Like Streamlit's st.* widgets, but streamed through WebSocket.
"""
import json
from typing import Any, Callable


class Widget:
    """Base class for all interactive widgets."""

    __slots__ = ("_type", "_id", "_props")

    def __init__(self, wtype: str, **props):
        self._type = wtype
        self._id = f"w_{wtype}_{id(self):x}"
        self._props = props

    def to_payload(self) -> dict:
        return {"type": "widget", "widget": self._type, "id": self._id, "props": self._props}

    def __repr__(self):
        return f"Widget({self._type}, id={self._id}, props={self._props})"


def _html_escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── Widget builders ────────────────────────────────────────────────────────────

def button(label: str, key: str = None, variant: str = "primary", disabled: bool = False) -> Widget:
    """
    Render a clickable button in the chat. When clicked, fires a `button_click`
    action back to the server.

    Args:
        label: Button text.
        key: Unique key for deduplication and server-side identification.
        variant: 'primary', 'secondary', or 'danger'.
        disabled: Whether the button is disabled.
    """
    return Widget("button", label=label, key=key or label, variant=variant, disabled=disabled)


def text_input(label: str, key: str, placeholder: str = "", value: str = "") -> Widget:
    """
    Render a text input field in the chat with a submit button.

    Args:
        label: Label shown above the input.
        key: Unique key for the component.
        placeholder: Placeholder text.
        value: Initial value.
    """
    return Widget("text_input", label=label, key=key, placeholder=placeholder, value=value)


def selectbox(label: str, options: list[str], key: str, index: int = 0) -> Widget:
    """
    Render a dropdown select box.

    Args:
        label: Label above the dropdown.
        options: List of string options.
        key: Unique key.
        index: Default selected index.
    """
    return Widget("selectbox", label=label, options=options, key=key, index=index)


def radio(label: str, options: list[str], key: str, index: int = 0) -> Widget:
    """
    Render a radio button group.

    Args:
        label: Label above the radio group.
        options: List of string options.
        key: Unique key.
        index: Default selected index.
    """
    return Widget("radio", label=label, options=options, key=key, index=index)


def checkbox(label: str, key: str, value: bool = False) -> Widget:
    """Render a checkbox."""
    return Widget("checkbox", label=label, key=key, value=value)


def slider(label: str, key: str, min_val: float = 0, max_val: float = 100, value: float = 50, step: float = 1) -> Widget:
    """Render a range slider."""
    return Widget("slider", label=label, key=key, min=min_val, max=max_val, value=value, step=step)


def progress(value: float, label: str = "") -> Widget:
    """
    Render a progress bar. Value should be between 0 and 1.

    Args:
        value: Progress from 0.0 to 1.0.
        label: Optional label.
    """
    return Widget("progress", value=max(0, min(1, value)), label=label)


def status(label: str, expanded: bool = False, state: str = "running") -> Widget:
    """
    Render a status container that can expand/collapse.

    Args:
        label: The status label.
        expanded: Whether expanded by default.
        state: One of 'running', 'complete', 'error'.
    """
    return Widget("status", label=label, expanded=expanded, state=state)


def table(data: list[dict], caption: str = "") -> Widget:
    """
    Render a data table.

    Args:
        data: List of dict rows. First row's keys become column headers.
        caption: Optional table caption.
    """
    if not data:
        return Widget("table", columns=[], rows=[], caption=caption)
    columns = list(data[0].keys())
    rows = [[row.get(col, "") for col in columns] for row in data]
    return Widget("table", columns=columns, rows=rows, caption=caption)


def markdown(content: str) -> Widget:
    """Render arbitrary markdown content inline."""
    return Widget("markdown", content=content)


def html(content: str) -> Widget:
    """Render raw HTML content inline in a sandboxed container."""
    return Widget("html", content=content)


def image(src: str, caption: str = "", width: int = None) -> Widget:
    """Render an image (URL, data URI, or file path served by the app)."""
    return Widget("image", src=src, caption=caption, width=width)


def divider() -> Widget:
    """Render a horizontal divider line."""
    return Widget("divider")


def metric(label: str, value: Any, delta: str = None) -> Widget:
    """
    Render a big metric number with optional delta indicator.

    Args:
        label: Metric label.
        value: The big number/string to display.
        delta: Optional delta string (e.g., "+12%", "-3.4").
    """
    return Widget("metric", label=label, value=str(value), delta=delta)


def columns(spec: list[float] = None) -> Widget:
    """
    Start a column layout. Returns a sentinel widget that signals
    the frontend to begin a column group. Subsequent widgets flow
    into columns until end_columns().

    Args:
        spec: List of relative widths, e.g. [1, 2, 1] for 3 columns.
    """
    return Widget("columns", ratios=spec or [1, 1])


def end_columns() -> Widget:
    """End a column layout group."""
    return Widget("columns_end")


def expander(label: str, expanded: bool = False) -> Widget:
    """Start an expandable container."""
    return Widget("expander", label=label, expanded=expanded)


def end_expander() -> Widget:
    """End an expandable container."""
    return Widget("expander_end")


def toast(message: str, icon: str = "info") -> Widget:
    """
    Show a temporary toast notification.

    Args:
        message: The toast message.
        icon: 'info', 'success', 'warning', or 'error'.
    """
    return Widget("toast", message=message, icon=icon)


def file_uploader(label: str, key: str, accept: str = None, multiple: bool = False) -> Widget:
    """
    Render a file upload drop zone.

    Args:
        label: Label text.
        key: Unique key.
        accept: File type filter (e.g., '.csv,.json' or 'image/*').
        multiple: Allow multiple files.
    """
    return Widget("file_uploader", label=label, key=key, accept=accept, multiple=multiple)


def spinner(label: str = "Loading...") -> Widget:
    """Render a spinner with label."""
    return Widget("spinner", label=label)


# ── Widget message helpers ─────────────────────────────────────────────────────

def _widget_to_json(w: Widget) -> str:
    return json.dumps(w.to_payload(), default=str, ensure_ascii=False)


def widget_message(*widgets: Widget) -> dict:
    """
    Build a message dict that can be sent via WebSocket as a widget payload.
    Used internally by ChatUI when tools/components return widgets.
    """
    return {
        "widgets": [w.to_payload() for w in widgets],
    }
