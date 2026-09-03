"""Fold the raw scorecards into a compact whole-field store: data/cards.json.

Shape:
  pars    - every distinct 18-digit par string seen all season (there are ~40)
  courses - every distinct course name
  cards   - "<playerId>_<tournamentId>" -> [ [n, total, toPar, parIdx, courseIdx, scores], ... ]

scores is one character a hole, base 36, so 10/11/12 become a/b/c and a hole with
no score is "0". Course index is -1 for the weeks that used a single course - the
tournament already names it. Yardage is dropped; the card does not show it.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

raw = json.loads((DATA / "scorecards_raw.json").read_text())
players = json.loads((DATA / "players.json").read_text())
tours = json.loads((DATA / "tournaments.json").read_text())

# a week counts as multi-course only if the event as a whole rotated
multi = {}
for t in tours:
    seen = set()
    for r in t["leaderboard"]:
        for rd in (raw.get(f'{r["id"]}_{t["id"]}') or {}).get("roundScores") or []:
            if rd.get("courseName"):
                seen.add(rd["courseName"])
    multi[t["id"]] = len(seen) > 1

pars, courses, cards = {}, {}, {}
idx = lambda tab, v: tab.setdefault(v, len(tab))
B36 = "0123456789abcdefghijklmnopqrstuvwxyz"

kept = rounds_total = 0
for t in tours:
    tid = t["id"]
    for row in t["leaderboard"]:
        card = raw.get(f'{row["id"]}_{tid}')
        if not card:
            continue
        out = []
        for r in card.get("roundScores") or []:
            holes = (r["firstNine"]["holes"] or []) + (r["secondNine"]["holes"] or [])
            if not holes:
                continue
            # firstNine is the player's first nine PLAYED, so a two-tee start puts
            # holes 10-18 first. 20% of rounds. Re-order by the actual hole number.
            holes.sort(key=lambda h: h.get("holeNumber") or 0)
            scores = [int(h["score"]) if str(h["score"]).isdigit() else 0 for h in holes]
            if not any(scores):
                continue      # alternate-shot rounds record no individual holes
            par = [int(h["par"]) for h in holes]
            tot = int(r["total"]) if str(r.get("total") or "").isdigit() else sum(scores)
            tp = r.get("scoreToPar")
            if tp == "E":
                tp = 0
            elif str(tp or "").lstrip("+-").isdigit():
                tp = int(tp)
            else:
                tp = tot - sum(p for p, s in zip(par, scores) if s)
            out.append([
                r.get("roundNumber"),
                tot,
                tp,
                idx(pars, "".join(map(str, par))),
                idx(courses, r["courseName"]) if multi[tid] and r.get("courseName") else -1,
                "".join(B36[min(v, 35)] for v in scores),
            ])
        if out:
            cards[f'{row["id"]}_{tid}'] = out
            kept += 1
            rounds_total += len(out)

out = {"pars": list(pars), "courses": list(courses), "cards": cards}
(DATA / "cards.json").write_text(json.dumps(out, separators=(",", ":")))
size = (DATA / "cards.json").stat().st_size / 1024

# ---- season scoring tally: the player's own card, so still the top 70 only
for p in players:
    tally = {"eagle": 0, "birdie": 0, "par": 0, "bogey": 0, "dbl": 0, "holes": 0}
    shots = 0
    for e in p["events"]:
        e.pop("card", None)                   # the store owns the cards now
        if str(e.get("total") or "").isdigit():
            shots += int(e["total"])          # official strokes, independent of the cards
        for r in cards.get(f'{p["id"]}_{e["tid"]}') or []:
            par = [int(c) for c in list(pars)[r[3]]]
            for i, ch in enumerate(r[5]):
                v = int(ch, 36)
                if not v:
                    continue
                d = v - par[i]
                tally["holes"] += 1
                tally["eagle" if d <= -2 else "birdie" if d == -1 else "par" if d == 0
                      else "bogey" if d == 1 else "dbl"] += 1
    p["scoring"] = {"shots": shots, **tally}

(DATA / "players.json").write_text(json.dumps(players, separators=(",", ":")))

field = sum(len(t["leaderboard"]) for t in tours)
ours = sum(1 for p in players for e in p["events"] if f'{p["id"]}_{e["tid"]}' in cards)
print(f"cards.json {size:,.0f} KB · {kept}/{field} scorecards, {rounds_total} rounds")
print(f"  par strings {len(pars)} · courses {len(courses)} · multi-course weeks "
      f"{sum(multi.values())}/{len(tours)}")
print(f"  of the FedExCup 70: {ours} cards")
print(f"players.json {(DATA/'players.json').stat().st_size/1024:,.0f} KB")
