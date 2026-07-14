"""Split extracted CSS into modular files by known section comments."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lines = (ROOT / "chatui/ui/_extracted.css").read_text(encoding="utf-8").splitlines(keepends=True)

# (line_index_0_based start, filename) — ordered by appearance
# First match wins when scanning from top; use absolute starts.
SECTION_STARTS = [
    (0, "00-tokens.css"),  # :root, base, a11y prefs
    # App shell starts at comment
]

# Find line numbers for markers
markers = {
    "tokens": 0,
}
for i, line in enumerate(lines):
    s = line.strip()
    if "App shell" in s and s.startswith("/*"):
        markers["shell"] = i
    elif "Sidebar" in s and s.startswith("/*") and "──" in s:
        markers["sidebar"] = i  # still shell
    elif "Main" in s and s.startswith("/*") and "──" in s:
        markers["main"] = i
    elif "Messages" in s and s.startswith("/*") and "──" in s:
        markers["messages"] = i
    elif s == "/* Markdown — vertical rhythm from --lh-prose */":
        markers["markdown"] = i  # keep with messages
    elif s == "/* Thinking */":
        markers["tools"] = i
    elif s == "/* Tool cards */":
        markers.setdefault("tools", i)
    elif s == "/* Widgets */":
        markers["widgets"] = i
    elif s == "/* Toasts */":
        markers["composer"] = i
    elif s == "/* Composer */":
        markers.setdefault("composer", i)
    elif s == "/* Connection banner */":
        markers.setdefault("composer", i)
    elif s == "/* Menu button */":
        markers.setdefault("composer", i)
    elif s == "/* Scrollbars */":
        markers["responsive"] = i

print("markers:", {k: v + 1 for k, v in markers.items()})

# Ordered cut points: (start_line, file)
cuts = [
    (0, "00-tokens.css"),
    (markers["shell"], "01-shell.css"),  # includes sidebar
    (markers["main"], "02-main.css"),
    (markers["messages"], "03-messages.css"),  # messages + markdown
    (markers["tools"], "04-tools.css"),  # thinking + tool cards + components
    (markers["widgets"], "05-widgets.css"),
    (markers["composer"], "06-composer.css"),  # toasts + composer + conn + menu
    (markers["responsive"], "07-responsive.css"),
]
cuts.sort(key=lambda x: x[0])

out_dir = ROOT / "chatui/ui/css"
# clean previous
for p in out_dir.glob("*.css"):
    p.unlink()

for i, (start, fname) in enumerate(cuts):
    end = cuts[i + 1][0] if i + 1 < len(cuts) else len(lines)
    body = "".join(lines[start:end])
    path = out_dir / fname
    # append if same fname appears twice (shouldn't)
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8") + body, encoding="utf-8")
    else:
        path.write_text(body, encoding="utf-8")
    print(f"  {fname:22s} lines {start+1:4d}-{end:4d}  ({end-start:4d} lines)")

manifest = [f for _, f in cuts]
# unique preserve order
seen = set()
ordered = []
for f in manifest:
    if f not in seen:
        seen.add(f)
        ordered.append(f)
(out_dir / "manifest.txt").write_text("\n".join(ordered) + "\n", encoding="utf-8")

# verify round-trip
rebuilt = "".join((out_dir / f).read_text(encoding="utf-8") for f in ordered)
original = "".join(lines)
if rebuilt == original:
    print("ROUND-TRIP OK")
else:
    print("ROUND-TRIP MISMATCH", len(rebuilt), len(original))
    # find first diff
    for i, (a, b) in enumerate(zip(rebuilt, original)):
        if a != b:
            print("first diff at", i, repr(a), repr(b))
            break
    if len(rebuilt) != len(original):
        print("len diff", len(rebuilt) - len(original))
