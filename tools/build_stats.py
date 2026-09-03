"""Merge the 2026 season stats into players.json.

Strokes Gained: Around the Green is not published in the overview, but strokes
gained is additive by definition, so ARG = Total - OffTee - Approach - Putting.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

raw = json.loads((DATA / "stats_raw.json").read_text())
players = json.loads((DATA / "players.json").read_text())

SG = {"SG: Total": "total", "SG: Off The Tee": "ott",
      "SG: Approach to Green": "app", "SG: Putting": "putt"}

GROUPS = [
    ("Driving",   ["Driving Distance", "Driving Accuracy", "Total Driving"]),
    ("Approach",  ["GIR %", "Proximity", "Approach > 200 yds"]),
    ("Short game", ["Scrambling", "Sand Save %", "Scrambling from rough"]),
    ("Putting",   ["Putting Avg", "Putts Per Round", "One-putt %"]),
    ("Scoring",   ["Scoring Average", "Birdie Average", "Par 4"]),
]

missing = []
for p in players:
    ov = raw.get(p["id"]) or []
    by = {s["title"]: s for s in ov}
    if not all(t in by for t in SG):
        missing.append(p["name"])
        continue
    sg = {k: {"v": float(by[t]["value"]), "r": by[t]["rank"]} for t, k in SG.items()}
    sg["arg"] = {"v": round(sg["total"]["v"] - sg["ott"]["v"]
                            - sg["app"]["v"] - sg["putt"]["v"], 3), "r": None}
    p["sg"] = sg
    p["stats"] = [[g, [[t, by[t]["value"], by[t]["rank"]] for t in items if t in by]]
                  for g, items in GROUPS]

(DATA / "players.json").write_text(json.dumps(players, separators=(",", ":")))
print(f"stats on {len(players) - len(missing)}/{len(players)} players "
      f"-> players.json {(DATA / 'players.json').stat().st_size/1024:,.0f} KB")
print(f"missing: {missing or 'none'}")
best = max(players, key=lambda p: p["sg"]["total"]["v"])
print(f"best SG: Total -> {best['name']} {best['sg']['total']['v']:+.3f} "
      f"(rank {best['sg']['total']['r']}), ARG {best['sg']['arg']['v']:+.3f}")
