"""Merge points list + bio + season stats + OWGR into the final top-70 player dataset."""
import json, pathlib, re, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = ROOT / "data"
TOP = 70

FOLD = {"ø": "o", "æ": "ae", "å": "a", "ß": "ss", "ł": "l", "đ": "d", "ð": "d", "þ": "th"}


def norm(s):
    s = "".join(FOLD.get(c, FOLD.get(c.lower(), c)) for c in (s or ""))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", s.lower())


def key2(name):
    """Surname + first initial — matches Nico/Nicolas, Sam/Samuel."""
    parts = (name or "").split()
    return (norm(parts[-1]), norm(parts[0])[:1]) if parts else ("", "")


points = json.loads((data / "points_list.json").read_text())[:TOP]
raw = json.loads((data / "players_raw.json").read_text())
standings = {p["id"]: p for p in json.loads((data / "standings_raw.json").read_text())}
owgr = json.loads((data / "owgr_raw.json").read_text())
ow_full = {norm(o["name"]): o for o in owgr}
ow_k2 = {}
for o in owgr:
    ow_k2.setdefault(key2(o["name"]), o)


def widget_map(res):
    """Flatten the season 'widgets' blocks into one label->value dict."""
    out = {}
    for w in res.get("widgets") or []:
        for d in w.get("data") or []:
            out[d["label"]] = d["data"]
    return out


players = []
for p in points:
    pid = p["id"]
    rec = raw[pid]
    res = rec.get("results") or {}
    bio = res.get("summaryData", {}).get("summaryData", {})
    st = standings.get(pid, {})
    w = widget_map(res)

    o = ow_full.get(norm(p["name"])) or ow_k2.get(key2(p["name"]))

    recap = []
    for grp in (res.get("seasonRecap") or {}).get("items", []):
        if grp.get("year") == 2026:
            recap = [{"tid": i.get("tournamentId"), "title": i.get("title"), "body": i.get("body")}
                     for i in grp.get("items", []) if i.get("body")]

    highlights = {h["title"]: h["data"] for h in bio.get("careerHighlights", [])
                  if isinstance(h, dict) and "data" in h}

    players.append({
        "id": pid,
        "name": p["name"],
        "first": st.get("first"), "last": st.get("last"),
        "country": st.get("country"), "flag": st.get("flag"),
        "rank": p["pointsRank"],
        "points": p["points"],
        "officialRank": p["officialRank"],
        "owgr": ({"rank": o["rank"], "avg": o["avg"], "total": o["total"],
                  "events": o["events"], "lastWeek": o["lastWeek"]} if o else None),
        "bio": {
            "age": bio.get("age"), "born": bio.get("born"),
            "birthplace": bio.get("birthplace"), "college": bio.get("college"),
            "turnedPro": bio.get("turnedPro"),
            "careerWins": highlights.get("PGA TOUR Wins"),
        },
        "season": {
            "events": w.get("Events"), "cuts": w.get("Cuts"),
            "money": w.get("Official Money"),
            "wins": w.get("Wins"), "second": w.get("2nd"), "third": w.get("3rd"),
            "top5": w.get("Top 5"), "top10": w.get("Top 10"), "top25": w.get("Top 25"),
            "wd": w.get("WD"), "dq": w.get("DQ"),
        },
        "events": p["events"],
        "recap": recap,
    })

(data / "players.json").write_text(json.dumps(players, separators=(",", ":")))
print(f"wrote {len(players)} players -> data/players.json "
      f"({(data / 'players.json').stat().st_size/1024:.0f} KB)")

no_owgr = [p["name"] for p in players if not p["owgr"]]
no_bio = [p["name"] for p in players if not p["bio"]["age"]]
no_money = [p["name"] for p in players if not p["season"]["money"]]
print(f"missing OWGR: {no_owgr or 'none'}")
print(f"missing bio:  {no_bio or 'none'}")
print(f"missing money:{no_money or 'none'}")
print(f"with recap prose: {sum(1 for p in players if p['recap'])}/{len(players)}")
print()
for p in players[:5]:
    o = p["owgr"]
    print(f'{p["rank"]:>3} {p["name"]:<22} {p["flag"]} pts {p["points"]:>9,.1f} '
          f'OWGR {o["rank"] if o else "-":>3}  {p["season"]["events"]} evts, '
          f'{p["season"]["wins"]}W, {p["season"]["money"]}')
