"""
ChatUI — Full production demo
Tools, components, widgets, session state, and event handlers.

Run:
    export GROQ_API_KEY=gsk_...
    python demo/demo_full.py
"""
import ast
import operator
import os
import random
from datetime import datetime

from chatui import (
    ChatUI,
    button,
    metric,
    progress,
    status,
    table,
)

app = ChatUI(
    provider="groq",
    api_key=os.getenv("GROQ_API_KEY"),
    title="ChatUI Pro",
    logo="\u25c6",
    subtitle="Production-ready chatbot with tools, widgets, and live components.",
    theme="manuscript",
    chips=[
        "What's the weather in Tokyo?",
        "Search database for 'customer'",
        "Show my dashboard",
        "Chart sales by month",
        "Show widgets",
    ],
    rate_limit=60,
)


# ── Safe calculator (no eval) ─────────────────────────────────────────────────

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Num):  # Python 3.9 compat
        return node.n
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only simple arithmetic is allowed")


# ═══════════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════════

@app.tool
def get_weather(city: str) -> dict:
    """Get current weather for any city worldwide."""
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Windy"]
    return {
        "city": city,
        "temperature": f"{random.randint(10, 35)}\u00b0C",
        "humidity": f"{random.randint(30, 90)}%",
        "condition": random.choice(conditions),
        "wind": f"{random.randint(0, 30)} km/h",
        "updated": "Just now",
    }


@app.tool
def search_database(query: str, limit: int = 5) -> dict:
    """Search the internal database for records matching the query."""
    n = max(1, min(int(limit or 5), 10))
    results = [
        {
            "id": i,
            "title": f"Result {i}: {query} match #{i}",
            "score": round(random.uniform(0.7, 0.99), 3),
        }
        for i in range(1, n + 1)
    ]
    return {"query": query, "total": len(results), "results": results}


@app.tool
def get_dashboard() -> dict:
    """Return the executive dashboard with KPIs and charts data."""
    return {
        "kpis": {
            "revenue": "$1,247,892",
            "users": "34,291",
            "churn": "2.1%",
            "nps": "72",
            "growth": "+12.4%",
        },
        "monthly_revenue": [
            {"month": "Jan", "value": 890000},
            {"month": "Feb", "value": 920000},
            {"month": "Mar", "value": 1010000},
            {"month": "Apr", "value": 980000},
            {"month": "May", "value": 1150000},
            {"month": "Jun", "value": 1247892},
        ],
        "top_products": [
            {"name": "Pro Plan", "revenue": 520000, "growth": "+8%"},
            {"name": "Enterprise", "revenue": 410000, "growth": "+15%"},
            {"name": "Add-ons", "revenue": 180000, "growth": "+22%"},
            {"name": "API Access", "revenue": 137892, "growth": "+5%"},
        ],
    }


@app.tool
def calculate(expression: str) -> dict:
    """Evaluate a simple math expression (numbers and + - * / only)."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


@app.tool
def show_widgets() -> tuple:
    """Render interactive demo widgets in the chat."""
    return (
        metric("Revenue", "$1.2M", delta="+12%"),
        metric("Users", "34.2k", delta="+8%"),
        metric("NPS", "72", delta="+3"),
        progress(0.78, label="Project completion"),
        status("Database sync complete", state="complete"),
        table(
            [
                {"product": "Pro", "mrr": "$42k"},
                {"product": "Team", "mrr": "$18k"},
            ],
            caption="Top plans",
        ),
        button("Refresh data", key="refresh"),
        button("Dismiss", key="cancel", variant="secondary"),
    )


# ═══════════════════════════════════════════════════════════════════
# COMPONENTS
# ═══════════════════════════════════════════════════════════════════

@app.component("chart")
def render_chart(data: dict) -> str:
    """Bar chart — pass labels, values, title."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    mx = max(values) if values else 1
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0">'
        f'<span style="width:80px;text-align:right;font-size:12px;color:var(--text-secondary)">{l}</span>'
        f'<div style="height:24px;background:var(--accent);border-radius:4px;min-width:2px;'
        f'width:{max(int(v / mx * 240), 4)}px;transition:width 0.3s var(--ease-out)"></div>'
        f'<span style="font-size:12px;color:var(--text-primary);font-weight:500">{v}</span></div>'
        for l, v in zip(labels, values)
    )
    return (
        f'<div>'
        f'<b style="font-size:14px;color:var(--text-primary);font-family:var(--font-serif)">'
        f'{data.get("title", "Chart")}</b>'
        f'<br><br>{bars}'
        f'</div>'
    )


@app.component("dashboard")
def render_dashboard(data: dict) -> str:
    """Render a professional dashboard with KPIs and charts."""
    kpis = data.get("kpis", {})
    monthly = data.get("monthly_revenue", [])
    products = data.get("top_products", [])

    kpi_html = "".join(
        f'<div style="flex:1;min-width:100px;padding:12px 16px;'
        f'background:var(--bg-elevated);border-radius:var(--radius-sm);'
        f'border:1px solid var(--border);">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--text-tertiary);margin-bottom:6px">{k}</div>'
        f'<div style="font-size:1.25rem;font-weight:700;color:var(--text-primary);'
        f'font-family:var(--font-serif)">{v}</div>'
        f'</div>'
        for k, v in kpis.items()
    )

    chart_html = render_chart({
        "title": "Monthly Revenue",
        "labels": [m["month"] for m in monthly],
        "values": [m["value"] for m in monthly],
    })

    product_rows = "".join(
        f'<tr><td style="padding:6px 12px;border:1px solid var(--border);font-weight:500">{p["name"]}</td>'
        f'<td style="padding:6px 12px;border:1px solid var(--border);font-family:var(--font-mono);font-size:13px">${p["revenue"]:,}</td>'
        f'<td style="padding:6px 12px;border:1px solid var(--border);font-family:var(--font-mono);'
        f'color:{"var(--success)" if "+" in p["growth"] else "var(--error)"}">{p["growth"]}</td></tr>'
        for p in products
    )

    return f"""
    <div>
      <h3 style="font-family:var(--font-serif);margin:0 0 1rem;font-size:1.3rem">Executive Dashboard</h3>
      <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.5rem">{kpi_html}</div>
      {chart_html}
      <br>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:0.5rem">
        <thead><tr style="background:var(--bg-elevated)">
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Product</th>
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Revenue</th>
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Growth</th>
        </tr></thead>
        <tbody>{product_rows}</tbody>
      </table>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════
# CONTEXT + EVENTS
# ═══════════════════════════════════════════════════════════════════

@app.context
def current_state():
    """Current session data and timestamp."""
    return {
        "session_id": app.session.id,
        "server_time": datetime.now().isoformat(),
        "click_count": app.session.get("click_count", 0),
        "last_button": app.session.get("last_button"),
    }


@app.on("button_click")
def handle_button(data: dict):
    """Track button clicks in session state."""
    key = data.get("key", "")
    app.session["last_button"] = key
    app.session["click_count"] = app.session.get("click_count", 0) + 1
    return {
        "clicked": key,
        "total_clicks": app.session["click_count"],
    }


@app.on("refresh")
def on_refresh(data: dict):
    """Handle the Refresh widget key specifically."""
    return (
        status("Refreshed", state="complete"),
        metric("Clicks", app.session.get("click_count", 0)),
    )


if __name__ == "__main__":
    app.run()
