"""Per-hole scoring for the whole field, per round, for every 2026 tournament.

courseStats -> courses[] -> roundHoleStats[] (All Rounds, R1..R4) -> holeStats[].
holeStats is typed as an interface, so the fields need an inline fragment on
CourseHoleStats or the query fails validation.
"""
import json, pathlib, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ENDPOINT = "https://orchestrator.pgatour.com/graphql"
KEYS = ["da2-gsrx5bibzbb4njvhl7t37wqyl4",
        "da2-teu6bwqcgzaobbu2aazt3i7lkq",
        "da2-fmi36ir4dvavljcurr2ofyiota"]

QUERY = """query($t:ID!){ courseStats(tournamentId:$t){ courses{
  courseId courseName par yardage hostCourse
  roundHoleStats{ roundHeader roundNum holeStats{ ... on CourseHoleStats {
    courseHoleNum parValue yards scoringAverage scoringAverageDiff
    eagles birdies pars bogeys doubleBogey rank } } } } } }"""


def fetch(tid):
    body = json.dumps({"query": QUERY, "variables": {"t": tid}}).encode()
    for a in range(3):
        try:
            req = urllib.request.Request(ENDPOINT, body, {
                "content-type": "application/json", "x-api-key": KEYS[a % len(KEYS)],
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            d = json.loads(urllib.request.urlopen(req, timeout=45).read())
            if d.get("errors"):
                return (tid, None, json.dumps(d["errors"])[:120])
            return (tid, (d.get("data") or {}).get("courseStats"), None)
        except Exception as e:
            if a == 2:
                return (tid, None, str(e)[:80])
            time.sleep(1.5 * (a + 1))


tours = json.loads((DATA / "tournaments.json").read_text())
ids = [t["id"] for t in tours]
print(f"{len(ids)} tournaments ...")
out, errs, t0 = {}, [], time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for tid, cs, err in ex.map(fetch, ids):
        if err:
            errs.append((tid, err))
        elif cs:
            out[tid] = cs

(DATA / "holestats_raw.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"{len(out)}/{len(ids)} in {time.time()-t0:.0f}s "
      f"({(DATA / 'holestats_raw.json').stat().st_size/1024:.0f} KB raw)")
if errs:
    print("errors:", errs[:5])
empty = [t for t, c in out.items() if not (c.get("courses") or [])]
print(f"no course data: {len(empty)} {empty[:5]}")
