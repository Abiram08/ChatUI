"""Widget showcase — all widgets demonstrated with an echo bot (no API key needed).

Run: python demo/demo_widgets.py
"""
from chatui import chat, button, metric, progress, table, status, divider
from chatui import markdown, image, spinner, toast, actions, row, card, stack

WIDGETS_INTRO = """
## Widget Gallery

Try these examples (just type the number):

**1** — Metrics + Progress
**2** — Buttons + Actions
**3** — Table + Status
**4** — Card + Stack
"""

METRICS = (
    metric("Revenue", "$1.2M", delta="+12%"),
    metric("Users", "8,432", delta="+5.3%"),
    metric("Uptime", "99.9%", delta="+0.1%"),
    progress(0.78, label="Project completion"),
)

BUTTONS = actions(
    button("Primary", key="primary", variant="primary"),
    button("Secondary", key="secondary", variant="secondary"),
    button("Danger", key="danger", variant="danger"),
)

TABLE = table([
    {"Name": "Alice", "Role": "Admin", "Status": "Active"},
    {"Name": "Bob", "Role": "User", "Status": "Active"},
    {"Name": "Carol", "Role": "User", "Status": "Inactive"},
])

CARD_EXAMPLE = card(
    "Project Overview",
    stack(
        metric("Tasks", "24", delta="+3"),
        metric("Done", "18", delta="75%"),
    ),
)


def echo(message: str, session) -> str:
    """Echo with demo widgets based on user choice."""
    msg = message.strip()
    if msg == "1":
        return ("Showing metrics & progress:", METRICS)
    elif msg == "2":
        return ("Showing button variants:", BUTTONS)
    elif msg == "3":
        return ("Showing table & status:", TABLE, status("Online", state="complete"))
    elif msg == "4":
        return ("Showing card & stack:", CARD_EXAMPLE)
    elif msg.lower() in ("help", "?", "menu"):
        return WIDGETS_INTRO
    else:
        return f'You said: "{msg}"\n\nType a number (1-4) to see widgets, or "help" for the menu.'


chat(
    reply=echo,
    title="Widget Demo",
    subtitle="No API key needed — try numbers 1-4",
    theme="manuscript",
    chips=["1 — Metrics", "2 — Buttons", "3 — Table", "4 — Card"],
    welcome_title="Widget<br>Gallery",
)
