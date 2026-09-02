"""Rebuild the 2026 FedExCup season points list by summing per-event points."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = ROOT / "data"
raw = json.loads((data / "players_raw.json").read_text())
standings = {p["id"]: p for p in json.loads((data / "standings_raw.json").read_text())}


def columns(headers):
    """Flatten the header spec into a flat list of column labels."""
    cols = []
    for h in headers:
        if "groupLabel" in h:
            cols += [f'{h["groupLabel"]} {lbl}' for lbl in h["labels"]]
        else:
            cols.append(h["label"])
    return cols


def num(s):
    if not s or s in ("-", "E"):
        return 0.0
    try:
        return float(str(s).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


rows = []
for pid, rec in raw.items():
    res = rec.get("results") or {}
    tables = res.get("resultsData") or []
    events, pts_total = [], 0.0
    for tbl in tables:
        cols = columns(tbl["headers"])
        try:
            i_pts = cols.index("FedExCup Pts")
        except ValueError:
            i_pts = None
        idx = {c: n for n, c in enumerate(cols)}
        for r in tbl.get("data", []):
            f = r["fields"]
            get = lambda c: f[idx[c]] if c in idx and idx[c] < len(f) else None
            pts = num(f[i_pts]) if i_pts is not None and i_pts < len(f) else 0.0
            pts_total += pts
            events.append({
                "tid": r.get("tournamentId"),
                "date": get("Date"), "name": get("Tournament"),
                "pos": get("Pos"),
                "rounds": [get("R1"), get("R2"), get("R3"), get("R4")],
                "total": get("Total"), "toPar": get("To Par"),
                "pts": pts,
                "money": get("Winnings"),
            })
    st = standings.get(pid, {})
    rows.append({
        "id": pid,
        "name": st.get("name") or rec["bio"].get("firstName", "") + " " + rec["bio"].get("lastName", ""),
        "officialRank": st.get("officialRank"),
        "points": round(pts_total, 3),
        "nEvents": len(events),
        "events": events,
    })

rows.sort(key=lambda r: -r["points"])
for i, r in enumerate(rows, 1):
    r["pointsRank"] = i

(data / "points_list.json").write_text(json.dumps(rows, indent=1))
print(f"{len(rows)} players ranked by 2026 FedExCup points\n")
print(f"{'#':>3} {'name':<24} {'points':>10} {'evts':>4}  official")
for r in rows[:15]:
    print(f'{r["pointsRank"]:>3} {r["name"]:<24} {r["points"]:>10,.3f} {r["nEvents"]:>4}  {r["officialRank"]}')
