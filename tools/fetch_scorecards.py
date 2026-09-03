"""Pull hole-by-hole scorecards for every player-tournament via the PGA TOUR GraphQL API.

The API key ships in pgatour.com's own public JS bundle. If it stops working, reload any
pgatour.com page and, from the page context, fetch every script[src] and regex for
/da2-[a-z0-9]{20,}/  (see the pgatour-orchestrator-api note).
"""
import json, pathlib, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "scorecards_raw.json"
ENDPOINT = "https://orchestrator.pgatour.com/graphql"
KEYS = ["da2-gsrx5bibzbb4njvhl7t37wqyl4",
        "da2-teu6bwqcgzaobbu2aazt3i7lkq",
        "da2-fmi36ir4dvavljcurr2ofyiota"]

QUERY = """query($t:ID!,$p:ID!){ scorecardV3(tournamentId:$t, playerId:$p){
  totalStrokes
  roundScores{ roundNumber courseName parTotal total scoreToPar
    firstNine{ holes{ holeNumber par yardage score status } }
    secondNine{ holes{ holeNumber par yardage score status } } } } }"""


def fetch(args):
    tid, pid = args
    body = json.dumps({"query": QUERY, "variables": {"t": tid, "p": pid}}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(ENDPOINT, body, {
                "content-type": "application/json",
                "x-api-key": KEYS[attempt % len(KEYS)],
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            d = json.loads(urllib.request.urlopen(req, timeout=45).read())
            return (tid, pid, (d.get("data") or {}).get("scorecardV3"))
        except Exception:
            if attempt == 2:
                return (tid, pid, None)
            time.sleep(1.5 * (attempt + 1))


def main():
    # the whole field, not just the FedExCup 70: every leaderboard row already
    # carries the tour player id, so the job list is just the leaderboards.
    tours = json.loads((DATA / "tournaments.json").read_text())
    jobs = sorted({(t["id"], r["id"]) for t in tours
                   for r in t["leaderboard"] if r.get("id")})
    print(f"{len(jobs)} player-tournament scorecards ...")

    out, t0 = {}, time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, (tid, pid, card) in enumerate(ex.map(fetch, jobs), 1):
            if card and card.get("roundScores"):
                out[f"{pid}_{tid}"] = card
            if i % 200 == 0:
                print(f"  {i}/{len(jobs)}  ({time.time()-t0:.0f}s)")

    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"\n{len(out)}/{len(jobs)} scorecards -> {OUT.name} "
          f"({OUT.stat().st_size/1024/1024:.1f} MB) in {time.time()-t0:.0f}s")
    missing = [k for k in ("%s_%s",) if False]
    got = set(out)
    miss = [(t, p) for (t, p) in jobs if f"{p}_{t}" not in got]
    print(f"missing: {len(miss)}  {miss[:5]}")


if __name__ == "__main__":
    main()
