import os, random
from chatui import ChatUI

app = ChatUI(
    provider = "groq",
    api_key  = os.getenv("GROQ_API_KEY"),
    title    = "My Assistant",
    logo     = "✦",
)

@app.tool
def weather(city: str) -> dict:
    """Get current weather for any city."""
    return {"city": city, "temp": f"{random.randint(15, 35)}°C", "sky": random.choice(["Sunny", "Cloudy", "Rainy"])}

@app.tool
def calculate(expression: str) -> dict:
    """Evaluate any math expression."""
    return {"result": eval(expression, {"__builtins__": {}}, {})}

@app.component("chart")
def render_chart(data: dict) -> str:
    """Bar chart — pass labels, values, title."""
    labels, values = data.get("labels", []), data.get("values", [])
    mx = max(values) if values else 1
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<span style="width:80px;text-align:right;font-size:12px;color:var(--text-secondary)">{l}</span>'
        f'<div style="height:20px;background:var(--accent);border-radius:3px;width:{int(v/mx*220)}px"></div>'
        f'<span style="font-size:12px;color:var(--text-primary)">{v}</span></div>'
        for l, v in zip(labels, values)
    )
    return f'<div><b style="font-size:13px;color:var(--text-primary)">{data.get("title","")}</b><br><br>{bars}</div>'

app.run()
