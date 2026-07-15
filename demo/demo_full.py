"""Full demo — tools, components, widgets, events with real-ish data.

Uses Open-Meteo API (free, no key) for weather.
Uses in-memory dict for user lookup (clearly labeled as demo data).

Requires: GROQ_API_KEY or OPENAI_API_KEY or ANTHROPIC_API_KEY
Or: Ollama running on localhost:11434

Run: python demo/demo_full.py
"""
import httpx
from chatui import ChatUI, button, metric, progress, table, actions

app = ChatUI(provider="auto", title="Full Demo", subtitle="Tools + Widgets + Events")


@app.tool
def get_weather(city: str) -> dict:
    """Get current weather for a city using Open-Meteo (free, no API key).

    Args:
        city: City name (e.g., "Tokyo", "New York")
    """
    try:
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=5,
        )
        geo.raise_for_status()
        geo_data = geo.json()
        if not geo_data.get("results"):
            return {"error": f"City '{city}' not found"}
        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]

        weather = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
            },
            timeout=5,
        )
        weather.raise_for_status()
        w = weather.json()
        return {
            "city": city,
            "temperature": f"{w['current']['temperature_2m']}C",
            "wind_speed": f"{w['current']['wind_speed_10m']} km/h",
            "weather_code": w["current"]["weather_code"],
        }
    except Exception as e:
        return {"error": f"Weather lookup failed: {e}"}


# In-memory demo data (replace with your database in production)
_USERS = {
    "alice": {"role": "admin", "joined": "2024-01-15", "orders": 42},
    "bob": {"role": "user", "joined": "2024-03-22", "orders": 7},
    "carol": {"role": "user", "joined": "2024-06-08", "orders": 0},
}


@app.tool
def lookup_user(username: str) -> dict:
    """Look up a user by username. Demo uses in-memory data.

    Args:
        username: Username to look up (e.g., "alice", "bob")
    """
    return _USERS.get(username, {"error": f"User '{username}' not found"})


@app.tool
def show_dashboard() -> tuple:
    """Show a dashboard with metrics and a refresh button."""
    return (
        metric("Revenue", "$1.2M", delta="+12%"),
        metric("Users", "8,432", delta="+5.3%"),
        metric("Uptime", "99.9%", delta="+0.1%"),
        progress(0.78, label="Project completion"),
        actions(
            button("Refresh", key="refresh", variant="primary"),
            button("Export", key="export", variant="secondary"),
        ),
    )


@app.component("dashboard")
def dashboard(data: dict) -> str:
    """Render a custom dashboard component."""
    title = data.get("title", "Dashboard")
    return f"<div class='custom-dashboard'><h3>{title}</h3><p>Custom HTML component</p></div>"


@app.on("button_click")
def handle_button(data: dict):
    """Handle any button click."""
    key = data.get("key", "")
    if key == "refresh":
        return metric("Status", "Refreshed!", delta="just now")
    elif key == "export":
        return "Export started! Check your downloads."
    return f"Button clicked: {key}"


app.run()
