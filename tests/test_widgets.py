"""Unit tests for chatui.widgets — builders, collect/strip helpers."""
from __future__ import annotations

import pytest

from chatui.widgets import (
    Widget,
    button,
    checkbox,
    collect_widgets,
    columns,
    divider,
    end_columns,
    expander,
    metric,
    progress,
    radio,
    selectbox,
    spinner,
    status,
    strip_widgets,
    table,
    text_input,
    toast,
    widget_message,
    widget_payloads,
)


class TestBuilders:
    def test_button_defaults(self):
        w = button("Save")
        assert w.type == "button"
        assert w.props["label"] == "Save"
        assert w.props["key"] == "Save"
        assert w.props["variant"] == "primary"
        assert w.props["disabled"] is False

    def test_button_invalid_variant_falls_back(self):
        w = button("X", variant="neon")
        assert w.props["variant"] == "primary"

    def test_button_custom_key(self):
        w = button("Refresh data", key="refresh", variant="secondary")
        assert w.props["key"] == "refresh"
        assert w.props["variant"] == "secondary"

    def test_progress_clamps(self):
        assert progress(-1).props["value"] == 0.0
        assert progress(2).props["value"] == 1.0
        assert progress(0.5).props["value"] == 0.5

    def test_status_invalid_state(self):
        assert status("Sync", state="maybe").props["state"] == "running"

    def test_selectbox_index_clamped(self):
        w = selectbox("Pick", ["a", "b"], key="p", index=99)
        assert w.props["index"] == 1
        empty = selectbox("Empty", [], key="e", index=3)
        assert empty.props["index"] == 0

    def test_radio_index_clamped(self):
        w = radio("R", ["x", "y", "z"], key="r", index=-5)
        assert w.props["index"] == 0

    def test_table_from_rows(self):
        w = table([{"a": 1, "b": 2}, {"a": 3, "b": 4}], caption="T")
        assert w.props["columns"] == ["a", "b"]
        assert w.props["rows"] == [[1, 2], [3, 4]]
        assert w.props["caption"] == "T"

    def test_table_empty(self):
        w = table([])
        assert w.props["columns"] == []
        assert w.props["rows"] == []

    def test_metric_and_columns(self):
        m = metric("Revenue", "$1M", delta="+12%")
        assert m.props["value"] == "$1M"
        assert m.props["delta"] == "+12%"
        c = columns([2, 1])
        assert c.props["ratios"] == [2.0, 1.0]
        assert end_columns().type == "columns_end"

    def test_toast_icon_validation(self):
        assert toast("ok", icon="nope").props["icon"] == "info"
        assert toast("done", icon="success").props["icon"] == "success"

    def test_spinner_default_label(self):
        assert "Working" in spinner().props["label"]

    def test_text_input_and_checkbox(self):
        ti = text_input("Name", key="name", placeholder="Ada")
        assert ti.props["placeholder"] == "Ada"
        cb = checkbox("Agree", key="agree", value=True)
        assert cb.props["value"] is True

    def test_to_payload_shape(self):
        p = button("Go").to_payload()
        assert p["type"] == "widget"
        assert p["widget"] == "button"
        assert "id" in p and p["id"].startswith("w_button_")
        assert p["props"]["label"] == "Go"


class TestCollectStrip:
    def test_collect_none(self):
        assert collect_widgets(None) == []

    def test_collect_single(self):
        w = button("A")
        assert collect_widgets(w) == [w]

    def test_collect_nested(self):
        a, b = button("A"), metric("M", 1)
        got = collect_widgets([a, {"x": 1}, (b, divider())])
        assert [w.type for w in got] == ["button", "metric", "divider"]

    def test_strip_only_widgets(self):
        result = strip_widgets([button("A"), metric("M", 1)])
        assert result == {"ok": True, "ui": ["button", "metric"]}

    def test_strip_single_widget(self):
        assert strip_widgets(button("A")) == {"ok": True, "ui": ["button"]}

    def test_strip_mixed_keeps_data(self):
        result = strip_widgets([button("A"), {"city": "Tokyo"}])
        assert result == {"city": "Tokyo"}

    def test_strip_mixed_multiple_data(self):
        result = strip_widgets([button("A"), 1, 2])
        assert result == [1, 2]

    def test_strip_no_widgets(self):
        assert strip_widgets({"a": 1}) == {"a": 1}
        assert strip_widgets([1, 2]) == [1, 2]

    def test_widget_payloads_and_message(self):
        widgets = [button("A"), progress(0.5)]
        payloads = widget_payloads(widgets)
        assert len(payloads) == 2
        msg = widget_message(*widgets)
        assert "widgets" in msg
        assert msg["widgets"][0]["widget"] == "button"

    def test_widget_repr(self):
        w = expander("More")
        assert "expander" in repr(w)
