"""Fold the raw scorecards into players.json in a compact per-round shape.

Per round we keep: number, total, score-to-par, the par string (one digit a hole)
and the 18 hole scores. Course name only when a player saw more than one course
that week (Pebble Beach and friends rotate). Yardage is dropped - it would double
the payload for something the card does not show.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

raw = json.loads((DATA / "scorecards_raw.json").read_text())
players = json.loads((DATA / "players.json").read_text())

attached = rounds_total = 0
for p in players:
    for e in p["events"]:
        card = raw.get(f'{p["id"]}_{e["tid"]}')
        if not card:
            continue
        rounds, courses = [], set()
        for r in card.get("roundScores") or []:
            holes = (r["firstNine"]["holes"] or []) + (r["secondNine"]["holes"] or [])
            if not holes:
                continue
            scores = [int(h["score"]) if str(h["score"]).isdigit() else 0 for h in holes]
            if not any(scores):
                continue      # alternate-shot rounds record no individual holes
            courses.add(r.get("courseName") or "")
            rounds.append({
                "n": r.get("roundNumber"),
                "t": r.get("total"),
                "tp": r.get("scoreToPar"),
                "c": r.get("courseName") or "",
                "p": "".join(str(h["par"]) for h in holes),
                "s": scores,
            })
        if not rounds:
            continue
        # only carry the course name when the week used more than one
        if len(courses) <= 1:
            for r in rounds:
                r.pop("c", None)
        e["card"] = rounds
        rounds_total += len(rounds)
        attached += 1

(DATA / "players.json").write_text(json.dumps(players, separators=(",", ":")))
size = (DATA / "players.json").stat().st_size / 1024
print(f"attached {attached} scorecards ({rounds_total} rounds) -> players.json {size:,.0f} KB")

multi = sum(1 for p in players for e in p["events"]
            if e.get("card") and any("c" in r for r in e["card"]))
print(f"multi-course weeks: {multi}")
no_card = sum(1 for p in players for e in p["events"] if not e.get("card"))
print(f"events with no scorecard: {no_card}")
blank = sum(1 for p in players for e in p["events"] for r in (e.get("card") or [])
            if not any(r["s"]))
print(f"all-blank rounds retained (should be 0): {blank}")
