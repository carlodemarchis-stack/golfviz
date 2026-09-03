"""Fetch 2026 PGA TOUR season data from pgatour.com (__NEXT_DATA__) and owgr.com."""
import json, re, sys, time, urllib.request, pathlib
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "scratch" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SEASON = "2026"


def get(url, cache_key, binary=False):
    """Fetch with an on-disk cache so re-runs are cheap."""
    f = RAW / cache_key
    if f.exists() and f.stat().st_size > 0:
        return f.read_bytes() if binary else f.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(req, timeout=60).read()
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    f.write_bytes(body)
    return body if binary else body.decode("utf-8", "replace")


def next_data(html):
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]


def query(pp, name, pred=None):
    """Pull one react-query payload out of the dehydrated state."""
    for q in pp.get("dehydratedState", {}).get("queries", []):
        if q["queryKey"][0] == name and (pred is None or pred(q["queryKey"])):
            return q["state"]["data"]
    return None


# ---------------------------------------------------------------- standings
def fetch_standings():
    pp = next_data(get("https://www.pgatour.com/fedexcup/official-standings.html",
                       "standings.html"))
    meta = pp["tourCupMetaList"][0]
    rows = [p for p in meta["officialPlayers"] if p.get("__typename") == "TourCupCombinedPlayer"]
    out = []
    for p in rows:
        out.append({
            "id": p["id"],
            "first": p["firstName"], "last": p["lastName"],
            "name": p["displayName"], "short": p["shortName"],
            "country": p["country"], "flag": p["countryFlag"],
            "officialRank": p["rankingData"]["official"],
            "events": p["columnData"][0] if p["columnData"] else None,
            "wins": p["columnData"][3] if len(p["columnData"]) > 3 else None,
            "top10": p["columnData"][4] if len(p["columnData"]) > 4 else None,
        })
    return out


# ---------------------------------------------------------------- schedule
def fetch_schedule():
    pp = next_data(get("https://www.pgatour.com/schedule", "schedule.html"))
    d = query(pp, "schedule")
    return d["tournaments"]


# ---------------------------------------------------------------- owgr
def fetch_owgr(n=600):
    url = ("https://apiweb.owgr.com/api/owgr/rankings/getRankings"
           f"?pageSize={n}&pageNumber=1&sortString=Rank+ASC&regionId=0&countryId=0&pageKey=1")
    d = json.loads(get(url, "owgr.json"))
    return [{
        "rank": r["rank"],
        "name": r["player"]["fullName"],
        "country": r["player"]["country"]["name"],
        "ioc": r["player"]["country"]["iocCode"] or "",
        "avg": r["pointsAverage"],
        "total": round(r["pointsTotal"], 2),
        "events": r["divisorApplied"],
        "lastWeek": r["lastWeekRank"],
    } for r in d["rankingsList"]]


# ---------------------------------------------------------------- player
def fetch_player(pid):
    html = get(f"https://www.pgatour.com/player/{pid}/x/results", f"player_{pid}.html")
    pp = next_data(html)
    res = query(pp, "playerProfileResults",
                lambda k: len(k) > 3 and k[3].get("season") == SEASON)
    if res is None:
        res = query(pp, "playerProfileResults")
    bio = (res or {}).get("summaryData", {}).get("summaryData", {})
    return {"id": pid, "bio": bio, "results": res}


# ---------------------------------------------------------------- leaderboard
def fetch_leaderboard(tid):
    html = get(f"https://www.pgatour.com/tournaments/{SEASON}/x/{tid}/leaderboard",
               f"lb_{tid}.html")
    pp = next_data(html)
    d = query(pp, "leaderboard")
    if d is None:
        return fetch_team_leaderboard(tid, pp)
    rows = []
    for r in d.get("players", []):
        if r.get("__typename") != "PlayerRowV3":
            continue
        pl, sc = r["player"], r["scoringData"]
        rows.append({
            "id": pl["id"], "name": pl["displayName"], "flag": pl.get("countryFlag"),
            "amateur": pl.get("amateur", False),
            "pos": sc.get("position"), "total": sc.get("total"),
            "totalSort": sc.get("totalSort"), "strokes": sc.get("totalStrokes"),
            "rounds": sc.get("rounds"),
        })
    return {"tid": tid, "winner": d.get("winner"), "players": rows,
            "courses": d.get("courses"), "rounds": d.get("rounds")}


def fetch_team_leaderboard(tid, pp):
    """The Zurich Classic is two-man teams and uses a different query."""
    d = query(pp, "teamStrokePlayLeaderboard")
    if d is None:
        return {"tid": tid, "players": [], "winner": None, "team": True}
    rows = []
    for r in d.get("leaderboard", []):
        if r.get("__typename") != "TspTeamRow":
            continue
        mates = [{"id": p["id"], "name": p["displayName"], "flag": p.get("countryFlag")}
                 for p in r.get("players", [])]
        rows.append({
            "id": r["teamId"],
            "name": " / ".join(m["name"] for m in mates),
            "flag": mates[0]["flag"] if mates else None,
            "members": mates,
            "pos": r.get("position"), "total": r.get("total"),
            "totalSort": r.get("totalSort"), "strokes": r.get("totalStrokes"),
            "rounds": r.get("rounds"),
        })
    w = d.get("winner") or {}
    team = w.get("winningTeam") or []
    winner = {
        "firstName": team[0].get("firstName") if team else "",
        "lastName": " / ".join(f'{p["firstName"]} {p["lastName"]}' for p in team),
        "countryFlag": team[0].get("countryFlag") if team else None,
        "totalScore": w.get("totalScore"), "totalStrokes": w.get("totalStrokes"),
        "purse": w.get("purse"), "points": w.get("points"),
        "ids": [p["id"] for p in team],
    } if w else None
    return {"tid": tid, "winner": winner, "players": rows, "team": True}


# ---------------------------------------------------------------- career
def fetch_career(pid):
    html = get(f"https://www.pgatour.com/player/{pid}/x/career", f"career_{pid}.html")
    pp = next_data(html)
    d = query(pp, "playerProfileCareer")
    return {"id": pid, "career": (d or {}).get("career")}


# ---------------------------------------------------------------- stats
def fetch_stats(pid):
    html = get(f"https://www.pgatour.com/player/{pid}/x/stats", f"stats_{pid}.html")
    pp = next_data(html)
    d = query(pp, "playerProfileStats",
              lambda k: len(k) > 1 and k[1].get("season") == SEASON)
    return {"id": pid, "overview": (d or {}).get("statsOverview")}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = ROOT / "data"

    if cmd in ("all", "base"):
        st = fetch_standings()
        (data / "standings_raw.json").write_text(json.dumps(st, indent=1))
        print(f"standings: {len(st)} players")
        sched = fetch_schedule()
        (data / "schedule_raw.json").write_text(json.dumps(sched, indent=1))
        print(f"schedule: {len(sched)} tournaments")
        owgr = fetch_owgr()
        (data / "owgr_raw.json").write_text(json.dumps(owgr, indent=1))
        print(f"owgr: {len(owgr)} players")

    if cmd in ("all", "stats"):
        top = json.loads((data / "players.json").read_text())
        ids = [p["id"] for p in top]
        print(f"fetching {len(ids)} stats pages ...")
        out = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            for i, r in enumerate(ex.map(fetch_stats, ids), 1):
                out[r["id"]] = r["overview"]
                if i % 20 == 0:
                    print(f"  {i}/{len(ids)}")
        (data / "stats_raw.json").write_text(json.dumps(out, indent=1))
        print(f"stats: {sum(1 for v in out.values() if v)}/{len(out)}")

    if cmd in ("all", "career"):
        top = json.loads((data / "players.json").read_text())
        ids = [p["id"] for p in top]
        print(f"fetching {len(ids)} career pages ...")
        out = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            for i, r in enumerate(ex.map(fetch_career, ids), 1):
                out[r["id"]] = r["career"]
                if i % 20 == 0:
                    print(f"  {i}/{len(ids)}")
        (data / "career_raw.json").write_text(json.dumps(out, indent=1))
        print(f"career: {sum(1 for v in out.values() if v)}/{len(out)} with data")

    if cmd in ("all", "tournaments"):
        sched = json.loads((data / "schedule_raw.json").read_text())
        season = [t for t in sched if t["status"] == "COMPLETED"]
        print(f"fetching {len(season)} leaderboards ...")
        out = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            for r in ex.map(fetch_leaderboard, [t["tournamentId"] for t in season]):
                out[r["tid"]] = r
        (data / "leaderboards_raw.json").write_text(json.dumps(out, indent=1))
        print(f"leaderboards: {len(out)}")

    if cmd in ("all", "players"):
        st = json.loads((data / "standings_raw.json").read_text())
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        ids = [p["id"] for p in st[:limit]]
        print(f"fetching {len(ids)} player result pages ...")
        got = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            for i, r in enumerate(ex.map(fetch_player, ids), 1):
                got[r["id"]] = r
                if i % 10 == 0:
                    print(f"  {i}/{len(ids)}")
        (data / "players_raw.json").write_text(json.dumps(got, indent=1))
        print(f"players: {len(got)}")


if __name__ == "__main__":
    main()
