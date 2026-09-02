"""Download player portraits, tournament logos and course beauty shots."""
import json, pathlib, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
data, img = ROOT / "data", ROOT / "img"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"

PORTRAIT = "c_thumb,g_face,w_700,h_900,z_0.45,q_auto:good"
CDN = "https://pga-tour-res.cloudinary.com/image/upload"
ORG = "https://res.cloudinary.com/pgatour-prod/image/upload"


def grab(args):
    url, dest = args
    dest = pathlib.Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return ("cached", dest.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        body = urllib.request.urlopen(req, timeout=60).read()
        if len(body) < 200:
            return ("empty", dest.name)
        dest.write_bytes(body)
        return ("ok", dest.name)
    except Exception as e:
        return (f"FAIL {e}", dest.name)


players = json.loads((data / "players.json").read_text())
tours = json.loads((data / "tournaments.json").read_text())

jobs = []
ids = {p["id"] for p in players}
for t in tours:                                   # champions may sit outside the top 70
    ch = t["champion"]
    for pid in (ch.get("ids") or ([ch["id"]] if ch.get("id") else [])):
        ids.add(pid)
for pid in sorted(ids):
    jobs.append((f"{CDN}/{PORTRAIT}/headshots_{pid}.webp", img / "full" / f"{pid}.webp"))
    jobs.append((f"{CDN}/c_thumb,g_face,w_240,h_240,z_0.7,q_auto:good/headshots_{pid}.webp",
                 img / "face" / f"{pid}.webp"))
for t in tours:
    if t["logo"]:
        jobs.append((f"{ORG}/{t['logo']}.png", img / "logo" / f"{t['id']}.png"))
    if t["beauty"]:
        jobs.append((f"{CDN}/c_fill,w_1400,q_auto:good/{t['beauty']}.webp",
                     img / "course" / f"{t['id']}.webp"))

print(f"{len(jobs)} assets ({len(ids)} players, {len(tours)} tournaments) ...")
res = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, r in enumerate(ex.map(grab, jobs), 1):
        res.append(r)
        if i % 50 == 0:
            print(f"  {i}/{len(jobs)}")
from collections import Counter
print(dict(Counter(s.split()[0] for s, _ in res)))
bad = [(s, n) for s, n in res if s not in ("ok", "cached")]
if bad:
    print("problems:", bad[:20])
