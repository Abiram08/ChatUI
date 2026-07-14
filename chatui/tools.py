"""
chatui/tools.py
Tool registration, schema generation, and component renderers.

Keep this module small: register Python functions, build provider schemas,
execute tools safely, render named HTML components.
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Optional, Union, get_args, get_origin, get_type_hints


# Python → JSON Schema primitives
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def _json_type(python_type: Any) -> dict:
    """Map a Python annotation to a JSON Schema fragment."""
    if python_type is None or python_type is inspect.Parameter.empty:
        return {"type": "string"}

    origin = get_origin(python_type)
    args = get_args(python_type)

    # Optional[T] / Union[T, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _json_type(non_none[0])
        return {"type": "string"}

    if origin is list:
        item = _json_type(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item}

    if origin is dict:
        return {"type": "object"}

    if python_type in _TYPE_MAP:
        return {"type": _TYPE_MAP[python_type]}

    # Typing aliases without origin (e.g. List on older hints already resolved)
    name = getattr(python_type, "__name__", "") or str(python_type)
    if name in ("List", "list"):
        return {"type": "array", "items": {"type": "string"}}
    if name in ("Dict", "dict"):
        return {"type": "object"}

    return {"type": "string"}


class ToolRegistry:
    """Holds @app.tool functions and builds Anthropic / OpenAI schemas."""

    def __init__(self) -> None:
        self._tools: dict[str, dict] = {}

    def register(self, fn: Callable) -> Callable:
        name = fn.__name__
        if name in self._tools:
            raise ValueError(f"Tool {name!r} is already registered")

        doc = (fn.__doc__ or f"Call the {name} function").strip()
        # First line is the short description for the model
        description = doc.split("\n", 1)[0].strip()

        hints: dict = {}
        try:
            hints = get_type_hints(fn)
        except Exception:
            pass

        sig = inspect.signature(fn)
        properties: dict = {}
        required: list = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            schema = _json_type(hints.get(param_name, str))
            # Prefer docstring-style param notes if present — keep schema minimal
            properties[param_name] = schema
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        self._tools[name] = {
            "fn": fn,
            "schema": {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
        return fn

    def get_schemas(self) -> list[dict]:
        """Anthropic-format tool schemas."""
        return [t["schema"] for t in self._tools.values()]

    def get_openai_schemas(self) -> list[dict]:
        """OpenAI-format tool schemas (Groq, Ollama, OpenAI)."""
        out = []
        for t in self._tools.values():
            s = t["schema"]
            out.append({
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s["input_schema"],
                },
            })
        return out

    def has_tools(self) -> bool:
        return bool(self._tools)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, inputs: dict) -> Any:
        """Run a tool. Never raises — returns {"error": ...} on failure."""
        entry = self._tools.get(name)
        if not entry:
            return {"error": f"Tool '{name}' not found"}
        try:
            raw = inputs if isinstance(inputs, dict) else {}
            return entry["fn"](**raw)
        except TypeError as e:
            return {"error": f"Bad arguments for '{name}': {e}"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def to_json(value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps({"result": str(value)}, ensure_ascii=False)


class ComponentRegistry:
    """
    Named HTML renderers.

    When the model returns only:
        {"component": "chart", "data": {...}}
    ChatUI calls the registered function and injects the HTML into the chat.
    """

    def __init__(self) -> None:
        self._renderers: dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Component name must be a non-empty string")
        self._renderers[name] = fn

    def has(self, name: str) -> bool:
        return name in self._renderers

    def has_any(self) -> bool:
        return bool(self._renderers)

    def names(self) -> list[str]:
        return list(self._renderers.keys())

    def render(self, name: str, data: Any) -> str:
        fn = self._renderers.get(name)
        if not fn:
            return (
                f"<p style='color:var(--error)'>"
                f"Component <code>{_esc(name)}</code> is not registered.</p>"
            )
        try:
            html = fn(data if data is not None else {})
            return html if isinstance(html, str) else str(html)
        except Exception as e:
            return (
                f"<p style='color:var(--error)'>"
                f"Component error in <code>{_esc(name)}</code>: {_esc(str(e))}</p>"
            )


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
