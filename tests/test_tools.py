"""Unit tests for ToolRegistry and ComponentRegistry."""
from __future__ import annotations

import pytest

from chatui.tools import ComponentRegistry, ToolRegistry, _json_type


class TestJsonType:
    def test_primitives(self):
        assert _json_type(str) == {"type": "string"}
        assert _json_type(int) == {"type": "integer"}
        assert _json_type(float) == {"type": "number"}
        assert _json_type(bool) == {"type": "boolean"}

    def test_list_and_dict(self):
        assert _json_type(list)["type"] == "array"
        assert _json_type(dict) == {"type": "object"}

    def test_optional(self):
        from typing import Optional

        assert _json_type(Optional[int]) == {"type": "integer"}

    def test_list_of(self):
        from typing import List

        schema = _json_type(List[str])
        assert schema["type"] == "array"
        assert schema["items"] == {"type": "string"}


class TestToolRegistry:
    def test_register_and_schema(self):
        reg = ToolRegistry()

        def get_weather(city: str, units: str = "c") -> dict:
            """Get weather for a city."""
            return {"city": city, "units": units}

        reg.register(get_weather)
        assert reg.has_tools()
        assert reg.names() == ["get_weather"]

        schemas = reg.get_schemas()
        assert len(schemas) == 1
        s = schemas[0]
        assert s["name"] == "get_weather"
        assert s["description"] == "Get weather for a city."
        assert "city" in s["input_schema"]["required"]
        assert "units" not in s["input_schema"]["required"]
        assert s["input_schema"]["properties"]["city"]["type"] == "string"

    def test_openai_schema_shape(self):
        reg = ToolRegistry()

        def ping() -> str:
            """Health check."""
            return "ok"

        reg.register(ping)
        oai = reg.get_openai_schemas()
        assert oai[0]["type"] == "function"
        assert oai[0]["function"]["name"] == "ping"

    def test_duplicate_raises(self):
        reg = ToolRegistry()

        def foo():
            """Foo."""
            return 1

        reg.register(foo)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(foo)

    def test_execute_success(self):
        reg = ToolRegistry()

        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        reg.register(add)
        assert reg.execute("add", {"a": 2, "b": 3}) == 5

    def test_execute_missing_tool(self):
        reg = ToolRegistry()
        out = reg.execute("nope", {})
        assert "error" in out

    def test_execute_bad_args(self):
        reg = ToolRegistry()

        def needs(x: int) -> int:
            """Needs x."""
            return x

        reg.register(needs)
        out = reg.execute("needs", {})
        assert "error" in out

    def test_execute_raises_becomes_error(self):
        reg = ToolRegistry()

        def boom():
            """Boom."""
            raise RuntimeError("kaboom")

        reg.register(boom)
        out = reg.execute("boom", {})
        assert out["error"] == "kaboom"

    def test_to_json(self):
        assert '"a"' in ToolRegistry.to_json({"a": 1})
        # non-serializable fallback
        class Odd:
            def __str__(self):
                return "odd"
        assert "odd" in ToolRegistry.to_json(Odd())


class TestComponentRegistry:
    def test_register_and_render(self):
        reg = ComponentRegistry()
        reg.register("card", lambda data: f"<div>{data.get('t', '')}</div>")
        assert reg.has("card")
        assert reg.has_any()
        assert reg.names() == ["card"]
        assert reg.render("card", {"t": "hi"}) == "<div>hi</div>"

    def test_missing_component(self):
        reg = ComponentRegistry()
        html = reg.render("missing", {})
        assert "not registered" in html
        assert "missing" in html

    def test_component_error(self):
        reg = ComponentRegistry()

        def bad(_data):
            raise ValueError("nope")

        reg.register("bad", bad)
        html = reg.render("bad", {})
        assert "Component error" in html
        assert "nope" in html

    def test_invalid_name(self):
        reg = ComponentRegistry()
        with pytest.raises(ValueError):
            reg.register("", lambda d: "")
