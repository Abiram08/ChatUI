"""
ChatUI v1.0 — Full Production Demo
Showcases tools, components, widgets, session state, and event handlers.
"""
import os
import random
import json
from chatui import ChatUI
from chatui.widgets import (
    button, text_input, progress, status, table, metric,
    divider, toast, file_uploader, image, selectbox, checkbox, slider, expander,
)

app = ChatUI(
    provider="groq",
    api_key=os.getenv("GROQ_API_KEY"),
    title="ChatUI Pro",
    logo="\u25c6",
    subtitle="Production-ready chatbot interface with tools, widgets, and live components.",
    theme="manuscript",
    chips=[
        "Show me widgets",
        "What's the weather in Tokyo?",
        "Generate a sales chart",
        "Show my dashboard",
        "Upload a file for analysis",
    ],
)

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
    results = [
        {"id": i, "title": f"Result {i}: {query} match #{i}", "score": round(random.uniform(0.7, 0.99), 3)}
        for i in range(1, min(limit + 1, 11))
    ]
    return {"query": query, "total": len(results), "results": results}


@app.tool
def get_dashboard() -> dict:
    """Return the executive dashboard with KPIs and charts data."""
    return {
        "kpis": {
            "revenue":     "$1,247,892",
            "users":       "34,291",
            "churn":       "2.1%",
            "nps":         "72",
            "growth":      "+12.4%",
            "tickets":     "47 open",
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
            {"name": "Pro Plan",       "revenue": 520000, "growth": "+8%"},
            {"name": "Enterprise",     "revenue": 410000, "growth": "+15%"},
            {"name": "Add-ons",        "revenue": 180000, "growth": "+22%"},
            {"name": "API Access",     "revenue": 137892, "growth": "+5%"},
        ],
    }


@app.tool
def show_widgets_demo() -> dict:
    """Demonstrate all available widget types in ChatUI."""
    return {
        "demo": True,
        "message": "Widgets should be rendered by the component below.",
    }


@app.tool
def process_file(name: str, description: str) -> dict:
    """Process an uploaded file by name."""
    return {
        "file": name,
        "status": "processed",
        "rows_parsed": random.randint(100, 5000),
        "columns_found": random.randint(3, 15),
    }


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
        f'<b style="font-size:14px;color:var(--text-primary)">{data.get("title", "Chart")}</b>'
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

    product_html = "".join(
        f'<tr><td style="padding:6px 12px;border:1px solid var(--border);font-weight:500">{p["name"]}</td>'
        f'<td style="padding:6px 12px;border:1px solid var(--border);font-family:var(--font-mono);font-size:13px">${p["revenue"]:,}</td>'
        f'<td style="padding:6px 12px;border:1px solid var(--border);font-family:var(--font-mono);'
        f'color:{"var(--success)" if "+" in p["growth"] else "var(--error)"}">{p["growth"]}</td></tr>'
        for p in products
    )

    return f"""
    <div>
      <h3 style="font-family:var(--font-serif);margin:0 0 1rem">Executive Dashboard</h3>
      <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.5rem">{kpi_html}</div>
      {chart_html}
      <br>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:0.5rem">
        <thead><tr style="background:var(--bg-elevated)">
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Product</th>
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Revenue</th>
          <th style="padding:8px 12px;border:1px solid var(--border);text-align:left">Growth</th>
        </tr></thead>
        <tbody>{product_html}</tbody>
      </table>
    </div>
    """


@app.component("widgets_demo")
def render_widgets_demo(data: dict) -> str:
    """Render a demo of all available widgets."""
    return "".join([
        button("Click Me", key="demo_btn").to_payload()["props"]["label"],
    ])


# ═══════════════════════════════════════════════════════════════════
# CONTEXT
# ═══════════════════════════════════════════════════════════════════

@app.context
def current_state():
    """Current session data and timestamp."""
    return {
        "session_id": app.session.id,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "user_agent": "ChatUI Demo",
    }


# ═══════════════════════════════════════════════════════════════════
# EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.on("button_click")
def handle_button(data: dict):
    key = data.get("key", "")
    app.session["last_button"] = key
    app.session["click_count"] = app.session.get("click_count", 0) + 1
    return {"clicked": key, "total_clicks": app.session["click_count"]}


@app.on("file_upload")
def handle_file(data: dict):
    files = data.get("files", [])
    if files:
        app.session["uploaded_files"] = [f["name"] for f in files]
    return {"received": len(files), "names": app.session["uploaded_files"]}


# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run()
