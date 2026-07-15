"""Tests for tool schema quality — Enum, Literal, docstring args, Pydantic."""
from __future__ import annotations

from enum import Enum
from typing import Literal
import pytest
from chatui.tools import ToolRegistry, _json_type, _parse_docstring_args


class TestDocstringArgs:
    def test_google_style(self):
        doc = """Get weather.

        Args:
            city: City name (e.g., "Tokyo")
            units: Temperature units

        Returns:
            dict with weather data
        """
        result = _parse_docstring_args(doc)
        assert result["city"] == 'City name (e.g., "Tokyo")'
        assert result["units"] == "Temperature units"

    def test_sphinx_style(self):
        doc = """Get weather.

        :param city: City name
        :param units: Temperature units
        """
        result = _parse_docstring_args(doc)
        assert result["city"] == "City name"
        assert result["units"] == "Temperature units"

    def test_no_args_section(self):
        doc = "Just a description."
        assert _parse_docstring_args(doc) == {}

    def test_empty_docstring(self):
        assert _parse_docstring_args("") == {}


class Units(str, Enum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


class TestEnumSupport:
    def test_enum_in_schema(self):
        schema = _json_type(Units)
        assert schema["type"] == "string"
        assert "celsius" in schema["enum"]
        assert "fahrenheit" in schema["enum"]

    def test_enum_in_tool_registration(self):
        registry = ToolRegistry()

        def get_weather(city: str, units: Units = Units.CELSIUS) -> dict:
            """Get weather.

            Args:
                city: City name
                units: Temperature units
            """
            return {"city": city}

        registry.register(get_weather)
        schemas = registry.get_schemas()
        props = schemas[0]["input_schema"]["properties"]
        assert "enum" in props["units"]
        assert "celsius" in props["units"]["enum"]


class TestLiteralSupport:
    def test_literal_in_schema(self):
        schema = _json_type(Literal["a", "b", "c"])
        assert schema["type"] == "string"
        assert schema["enum"] == ["a", "b", "c"]

    def test_literal_in_tool_registration(self):
        registry = ToolRegistry()

        def search(query: str, mode: Literal["fast", "deep"] = "fast") -> dict:
            """Search."""
            return {"query": query}

        registry.register(search)
        schemas = registry.get_schemas()
        props = schemas[0]["input_schema"]["properties"]
        assert props["mode"]["enum"] == ["fast", "deep"]


class TestParamDescriptions:
    def test_param_description_from_docstring(self):
        registry = ToolRegistry()

        def get_weather(city: str, units: str = "celsius") -> dict:
            """Get weather for a city.

            Args:
                city: City name (e.g., "Tokyo")
                units: Temperature units ("celsius" or "fahrenheit")
            """
            return {"city": city}

        registry.register(get_weather)
        schemas = registry.get_schemas()
        props = schemas[0]["input_schema"]["properties"]
        assert props["city"]["description"] == 'City name (e.g., "Tokyo")'
        assert "fahrenheit" in props["units"]["description"]

    def test_no_description_without_args_section(self):
        registry = ToolRegistry()

        def simple_tool(x: str) -> str:
            """Just do something."""
            return x

        registry.register(simple_tool)
        schemas = registry.get_schemas()
        props = schemas[0]["input_schema"]["properties"]
        assert "description" not in props["x"]


class TestPydanticSupport:
    def test_pydantic_model_as_tool(self):
        pytest.importorskip("pydantic")
        from pydantic import BaseModel, Field

        class WeatherRequest(BaseModel):
            """Get weather for a city."""
            city: str = Field(description="City name")
            units: str = Field(default="celsius", description="Temperature units")

        registry = ToolRegistry()
        # Pydantic models have model_json_schema
        registry.register(WeatherRequest)
        schemas = registry.get_schemas()
        assert schemas[0]["name"] == "WeatherRequest"
        assert "city" in schemas[0]["input_schema"]["properties"]
