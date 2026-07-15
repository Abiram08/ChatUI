"""Beginner demo — plain functions, no decorators, minimal mental load.

Requires: GROQ_API_KEY or OPENAI_API_KEY or ANTHROPIC_API_KEY
Or: Ollama running on localhost:11434

Run: python demo/demo_beginner.py
"""
from chatui import chat


def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def calculate(expression: str) -> str:
    """Safely evaluate a math expression.

    Args:
        expression: A math expression like '2 + 3 * 4'
    """
    import ast
    import operator

    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")

    tree = ast.parse(expression, mode="eval")
    return str(_eval(tree.body))


chat(
    tools=[get_time, calculate],
    title="Beginner Demo",
    subtitle="Plain functions, no decorators",
)
