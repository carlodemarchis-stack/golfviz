"""Compact the per-hole field stats onto tournaments.json.

Per course, per round set, each hole becomes one small array:
[hole, par, yards, scoringAvg, diffVsPar, eagles, birdies, pars, bogeys, doubles, rank]
holeStats also carries OUT/IN/TOTAL summary rows, which are dropped.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
raw = json.loads((DATA / "holestats_raw.json").read_text())
tours = json.loads((DATA / "tournaments.json").read_text())


def num(v, d=0.0):
    try:
        return round(float(v), 3)
    except (TypeError, ValueError):
        return d


attached = 0
for t in tours:
    cs = (raw.get(t["id"]) or {}).get("courses") or []
    courses = []
    for c in cs:
        rounds = []
        for r in c.get("roundHoleStats") or []:
            holes = [h for h in (r.get("holeStats") or [])
                     if h.get("courseHoleNum") and 1 <= h["courseHoleNum"] <= 18]
            if not holes:
                continue
            rounds.append({
                "r": r.get("roundHeader", "").replace("All Rounds", "All").replace("Round ", "R"),
                "h": [[h["courseHoleNum"], int(num(h["parValue"])), h.get("yards") or 0,
                       num(h["scoringAverage"]), num(h["scoringAverageDiff"]),
                       h.get("eagles") or 0, h.get("birdies") or 0, h.get("pars") or 0,
                       h.get("bogeys") or 0, h.get("doubleBogey") or 0, h.get("rank") or 0]
                      for h in sorted(holes, key=lambda x: x["courseHoleNum"])],
            })
        if rounds:
            courses.append({"name": c.get("courseName"), "par": c.get("par"),
                            "yards": c.get("yardage"), "host": bool(c.get("hostCourse")),
                            "rounds": rounds})
    if courses:
        t["holes"] = courses
        attached += 1

(DATA / "tournaments.json").write_text(json.dumps(tours, separators=(",", ":")))
kb = (DATA / "tournaments.json").stat().st_size / 1024
print(f"hole stats on {attached}/{len(tours)} tournaments -> tournaments.json {kb:,.0f} KB")
multi = [t["name"] for t in tours if len(t.get("holes") or []) > 1]
print(f"multi-course events: {len(multi)} {multi[:3]}")
t0 = next(t for t in tours if t["id"] == "R2026004")
c0 = t0["holes"][0]
print(f"\nsample — {t0['name']} / {c0['name']} par {c0['par']}")
print(f"  round sets: {[r['r'] for r in c0['rounds']]}")
allr = next(r for r in c0["rounds"] if r["r"] == "All")
hard = min(allr["h"], key=lambda h: h[10])
print(f"  hardest: hole {hard[0]} par {hard[1]} {hard[2]}y avg {hard[3]} ({hard[4]:+}) "
      f"— {hard[5]}E {hard[6]}B {hard[7]}P {hard[8]}Bo {hard[9]}D")
