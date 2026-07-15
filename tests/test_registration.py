"""Tests for plain-function registration and decorator equivalence."""
from __future__ import annotations

import pytest
from chatui import ChatUI
from chatui.exceptions import ChatUIRegistrationError


class TestPlainFunctionRegistration:
    def test_tools_list_at_init(self):
        def get_weather(city: str) -> dict:
            """Get weather."""
            return {"city": city}

        def get_time() -> str:
            """Get time."""
            return "12:00"

        app = ChatUI(provider="ollama", open_browser=False, tools=[get_weather, get_time])
        assert "get_weather" in app._registry.names()
        assert "get_time" in app._registry.names()

    def test_add_tools_varargs(self):
        def fn1(x: str) -> str:
            """Fn1."""
            return x

        def fn2(y: str) -> str:
            """Fn2."""
            return y

        app = ChatUI(provider="ollama", open_browser=False)
        app.add_tools(fn1, fn2)
        assert "fn1" in app._registry.names()
        assert "fn2" in app._registry.names()

    def test_add_tools_list(self):
        def fn1(x: str) -> str:
            """Fn1."""
            return x

        app = ChatUI(provider="ollama", open_browser=False)
        app.add_tools([fn1])
        assert "fn1" in app._registry.names()

    def test_components_dict_at_init(self):
        def render_chart(data: dict) -> str:
            return "<b>chart</b>"

        app = ChatUI(provider="ollama", open_browser=False, components={"chart": render_chart})
        assert app._components.has("chart")

    def test_on_dict_at_init(self):
        def handler(data: dict):
            return {"ok": True}

        app = ChatUI(provider="ollama", open_browser=False, on={"button_click": handler})
        assert "button_click" in app._on_handlers

    def test_reply_at_init(self):
        def echo(message: str, session) -> str:
            return message

        app = ChatUI(provider="auto", open_browser=False, reply=echo)
        assert app._reply_fn is not None
        assert app._client is None


class TestDecoratorEquivalence:
    def test_decorator_vs_plain_same_schema(self):
        # Define the function once, register two ways
        def get_weather(city: str) -> dict:
            """Get weather for a city."""
            return {"city": city}

        # Via decorator
        app1 = ChatUI(provider="ollama", open_browser=False)

        @app1.tool
        def weather_decorator(city: str) -> dict:
            """Get weather for a city."""
            return {"city": city}

        # Via plain list
        app2 = ChatUI(provider="ollama", open_browser=False, tools=[get_weather])

        # Both should produce identical schema structure
        s1 = app1._registry.get_schemas()[0]
        s2 = app2._registry.get_schemas()[0]
        assert s1["description"] == s2["description"]
        assert s1["input_schema"]["properties"]["city"] == s2["input_schema"]["properties"]["city"]
        assert s1["input_schema"]["required"] == s2["input_schema"]["required"]


class TestDuplicateValidation:
    def test_duplicate_tool_raises(self):
        def fn(x: str) -> str:
            """Fn."""
            return x

        app = ChatUI(provider="ollama", open_browser=False, tools=[fn])
        with pytest.raises(ChatUIRegistrationError, match="Tool"):
            app.add_tools(fn)

    def test_duplicate_component_raises(self):
        def render(data: dict) -> str:
            return "<b>test</b>"

        app = ChatUI(provider="ollama", open_browser=False, components={"test": render})
        with pytest.raises(ChatUIRegistrationError, match="Component"):
            app.register_component("test", render)


class TestBatchMethods:
    def test_add_components(self):
        def fn1(data): return "<b>1</b>"
        def fn2(data): return "<b>2</b>"

        app = ChatUI(provider="ollama", open_browser=False)
        app.add_components({"c1": fn1, "c2": fn2})
        assert app._components.has("c1")
        assert app._components.has("c2")

    def test_add_handlers(self):
        def h1(data): pass
        def h2(data): pass

        app = ChatUI(provider="ollama", open_browser=False)
        app.add_handlers({"click": h1, "submit": h2})
        assert "click" in app._on_handlers
        assert "submit" in app._on_handlers
