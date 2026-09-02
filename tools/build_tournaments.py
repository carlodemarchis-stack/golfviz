"""Merge schedule + leaderboards into the 37 FedExCup-season tournament cards."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = ROOT / "data"

sched = json.loads((data / "schedule_raw.json").read_text())
lbs = json.loads((data / "leaderboards_raw.json").read_text())

MAJORS = {"Masters Tournament", "PGA Championship", "U.S. Open", "The Open Championship"}
PLAYOFFS = {"FedEx St. Jude Championship", "BMW Championship", "TOUR Championship"}
SIGNATURE_PURSE = 20_000_000


def money(s):
    return int(re.sub(r"[^0-9]", "", s or "0") or 0)


def category(t):
    n = t["name"]
    if n in PLAYOFFS:
        return "playoff"
    if n in MAJORS:
        return "major"
    if n == "THE PLAYERS Championship":
        return "players"
    if money(t.get("purse")) >= SIGNATURE_PURSE:
        return "signature"
    if money(t.get("purse")) <= 5_000_000:
        return "opposite"
    return "full"


out = []
for t in sched:
    if t["status"] != "COMPLETED":
        continue
    tid = t["tournamentId"]
    lb = lbs.get(tid, {})
    w = lb.get("winner") or {}
    champs = t.get("champions") or [{}]      # the Zurich Classic is won by a two-man team
    champ = champs[0]
    c = t.get("courseData") or {}
    out.append({
        "id": tid,
        "name": t["name"],
        "date": t["displayDate"],
        "month": t["month"],
        "category": category(t),
        "purse": t.get("purse"),
        "course": c.get("name"),
        "city": c.get("city"),
        "state": c.get("stateCode"),
        "countryCode": c.get("countryCode"),
        "logo": (t.get("logo") or {}).get("imagePath"),
        "beauty": (t.get("beautyImageAsset") or {}).get("imagePath"),
        "team": lb.get("team", False),
        "champion": {
            "id": champ.get("playerId"),
            "name": " / ".join(c.get("displayName", "") for c in champs if c.get("displayName")),
            "earnings": t.get("championEarnings"),
            "score": w.get("totalScore"),
            "strokes": w.get("totalStrokes"),
            "points": w.get("points"),
            "flag": w.get("countryFlag"),
            "ids": w.get("ids") or [c.get("playerId") for c in champs if c.get("playerId")],
        },
        "field": len(lb.get("players", [])),
        "leaderboard": lb.get("players", []),
    })

out.sort(key=lambda t: list(sched).index(next(s for s in sched if s["tournamentId"] == t["id"])))
(data / "tournaments.json").write_text(json.dumps(out, separators=(",", ":")))

print(f"wrote {len(out)} tournaments -> data/tournaments.json "
      f"({(data / 'tournaments.json').stat().st_size/1024:.0f} KB)")
from collections import Counter
print("categories:", dict(Counter(t["category"] for t in out)))
print("missing beauty image:", [t["name"] for t in out if not t["beauty"]] or "none")
print("missing logo:", [t["name"] for t in out if not t["logo"]] or "none")
print("missing champion score:", [t["name"] for t in out if not t["champion"]["score"]] or "none")
