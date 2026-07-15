"""
chatui/tools.py
Tool registration, schema generation, and component renderers.

Keep this module small: register Python functions, build provider schemas,
execute tools safely, render named HTML components.
"""
from __future__ import annotations

import inspect
import json
import re
from enum import Enum
from typing import Any, Callable, Optional, Union, get_args, get_origin, get_type_hints

try:
    from typing import Literal
    _HAS_LITERAL = True
except ImportError:
    _HAS_LITERAL = False

try:
    from typing import Annotated
    _HAS_ANNOTATED = True
except ImportError:
    _HAS_ANNOTATED = False


# Python -> JSON Schema primitives
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def _parse_docstring_args(docstring: str) -> dict[str, str]:
    """Parse Google-style or Sphinx-style docstring Args section.

    Returns {param_name: description} dict.
    """
    if not docstring:
        return {}

    result = {}
    # Google-style: Args:\n  param: description
    match = re.search(
        r'(?:Args?:|Arguments?:|Parameters?:)\s*\n((?:\s+\S+.*\n?)+)',
        docstring
    )
    if match:
        args_section = match.group(1)
        for line in args_section.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # "param_name: description" or "param_name (type): description"
            m = re.match(r'^(\w+)(?:\s*\([^)]+\))?\s*[:\-]\s*(.+)$', line)
            if m:
                result[m.group(1)] = m.group(2).strip()
        return result

    # Sphinx-style: :param name: description
    for line in docstring.split('\n'):
        m = re.match(r'^:param\s+(\w+):\s*(.+)$', line.strip())
        if m:
            result[m.group(1)] = m.group(2).strip()

    return result


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

    # Literal["a", "b", "c"] -> {"type": "string", "enum": ["a", "b", "c"]}
    if _HAS_LITERAL and origin is Literal:
        values = list(args)
        if all(isinstance(v, str) for v in values):
            return {"type": "string", "enum": values}
        return {"enum": values}

    # Enum subclasses -> {"type": "string", "enum": [...]}
    if isinstance(python_type, type) and issubclass(python_type, Enum):
        return {"type": "string", "enum": [e.value for e in python_type]}

    # Annotated[T, Field(...)] -> extract constraints
    if _HAS_ANNOTATED and origin is not None:
        # Check if it's Annotated
        if hasattr(python_type, "__metadata__"):
            base_type = args[0] if args else str
            schema = _json_type(base_type)
            for meta in args[1:]:
                if hasattr(meta, "description"):
                    schema["description"] = meta.description
                if hasattr(meta, "ge"):
                    schema["minimum"] = meta.ge
                if hasattr(meta, "le"):
                    schema["maximum"] = meta.le
                if hasattr(meta, "min_length"):
                    schema["minLength"] = meta.min_length
                if hasattr(meta, "max_length"):
                    schema["maxLength"] = meta.max_length
                if hasattr(meta, "pattern"):
                    schema["pattern"] = meta.pattern
            return schema

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

        # Parse per-param descriptions from docstring Args section
        param_descs = _parse_docstring_args(doc)

        # Check if it's a Pydantic model (has model_json_schema)
        if hasattr(fn, "model_json_schema"):
            schema = fn.model_json_schema()
            self._tools[name] = {
                "fn": fn,
                "schema": {
                    "name": name,
                    "description": description,
                    "input_schema": schema,
                },
            }
            return fn

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
            # Add param description from docstring if available
            if param_name in param_descs:
                schema["description"] = param_descs[param_name]
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
