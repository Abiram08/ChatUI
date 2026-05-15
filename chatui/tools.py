"""
chatui/tools.py
Tool registration, schema generation, component registry, and context support.
"""
import inspect
import json
from typing import Any, Callable, get_type_hints

# Maps Python types to JSON Schema types
TYPE_MAP = {
    str:   "string",
    int:   "integer",
    float: "number",
    bool:  "boolean",
    list:  "array",
    dict:  "object",
}


class ToolRegistry:
    """Holds all registered @app.tool functions and generates AI-compatible schemas."""

    def __init__(self):
        self._tools: dict[str, dict] = {}  # name → {fn, schema}

    def register(self, fn: Callable) -> Callable:
        name = fn.__name__
        doc  = (fn.__doc__ or "").strip()
        hints = {}
        try:
            hints = get_type_hints(fn)
        except Exception:
            pass
        sig = inspect.signature(fn)

        properties: dict = {}
        required:   list = []

        for param_name, param in sig.parameters.items():
            if param_name == "return":
                continue
            python_type = hints.get(param_name, str)
            json_type   = TYPE_MAP.get(python_type, "string")
            properties[param_name] = {"type": json_type}
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "name": name,
            "description": doc or f"Call the {name} function",
            "input_schema": {
                "type":       "object",
                "properties": properties,
                "required":   required,
            },
        }
        self._tools[name] = {"fn": fn, "schema": schema}
        return fn

    # ── Schema formats ────────────────────────────────────────────────

    def get_schemas(self) -> list[dict]:
        """Anthropic-format tool schemas."""
        return [t["schema"] for t in self._tools.values()]

    def get_openai_schemas(self) -> list[dict]:
        """OpenAI-format tool schemas (used for Ollama, Groq, OpenAI)."""
        result = []
        for t in self._tools.values():
            s = t["schema"]
            result.append({
                "type": "function",
                "function": {
                    "name":        s["name"],
                    "description": s["description"],
                    "parameters":  s["input_schema"],
                },
            })
        return result

    # ── Utility ───────────────────────────────────────────────────────

    def has_tools(self) -> bool:
        return bool(self._tools)

    def execute(self, name: str, inputs: dict) -> Any:
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}
        try:
            return self._tools[name]["fn"](**inputs)
        except Exception as e:
            return {"error": str(e)}

    def to_json(self, value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value)


class ComponentRegistry:
    """
    Holds @app.component renderers.

    When the AI returns JSON like {"component": "chart", "data": {...}},
    ChatUI calls the registered renderer and injects the returned HTML
    directly into the chat bubble.
    """

    def __init__(self):
        self._renderers: dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
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
            return f"<p style='color:var(--error)'>Component <code>{name}</code> not registered.</p>"
        try:
            return fn(data)
        except Exception as e:
            return f"<p style='color:var(--error)'>Component error: {e}</p>"
