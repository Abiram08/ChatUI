"""Tests for layout helpers and chat-native widgets."""
from __future__ import annotations

import pytest
from chatui.widgets import (
    Widget, button, metric, actions, row, stack, card, choice, form, confirm,
)


class TestLayoutHelpers:
    def test_actions_creates_action_row(self):
        btn1 = button("OK", key="ok")
        btn2 = button("Cancel", key="cancel")
        w = actions(btn1, btn2)
        assert w.type == "actions"
        assert "children" in w.props
        assert len(w.props["children"]) == 2

    def test_row_creates_horizontal_group(self):
        m1 = metric("A", 1)
        m2 = metric("B", 2)
        w = row(m1, m2)
        assert w.type == "row"
        assert len(w.props["children"]) == 2

    def test_stack_creates_vertical_group(self):
        m1 = metric("A", 1)
        w = stack(m1)
        assert w.type == "stack"
        assert len(w.props["children"]) == 1

    def test_card_creates_surface(self):
        m = metric("A", 1)
        w = card("My Card", m)
        assert w.type == "card"
        assert w.props["title"] == "My Card"
        assert len(w.props["children"]) == 1

    def test_actions_has_stable_id(self):
        w = actions(button("OK"))
        assert w.id.startswith("actions_")

    def test_row_has_stable_id(self):
        w = row(metric("A", 1))
        assert w.id.startswith("row_")

    def test_duplicate_keys_raise(self):
        with pytest.raises(ValueError, match="Duplicate widget keys"):
            actions(
                button("OK", key="dup"),
                button("Also OK", key="dup"),
            )


class TestChatNativeWidgets:
    def test_choice_payload(self):
        w = choice("Pick one", ["A", "B", "C"], key="pick")
        assert w.type == "choice"
        assert w.props["label"] == "Pick one"
        assert w.props["options"] == ["A", "B", "C"]
        assert w.props["key"] == "pick"

    def test_form_payload(self):
        w = form(
            button("Submit", key="submit"),
            submit_key="myform",
        )
        assert w.type == "form"
        assert w.props["submit_key"] == "myform"
        assert len(w.props["fields"]) == 1

    def test_confirm_returns_actions(self):
        w = confirm("Are you sure?", "yes", "no")
        assert w.type == "actions"
        assert len(w.props["children"]) == 2
        # First button is primary, second is secondary
        assert w.props["children"][0]["props"]["variant"] == "primary"
        assert w.props["children"][1]["props"]["variant"] == "secondary"


class TestWidgetIdAcceptance:
    def test_widget_accepts_custom_id(self):
        w = Widget("custom", id="my_id", label="test")
        assert w.id == "my_id"

    def test_widget_generates_id_without_custom(self):
        w = Widget("custom", label="test")
        assert w.id.startswith("w_custom_")
