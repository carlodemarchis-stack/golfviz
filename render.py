"""Inject the built datasets into template.html -> index.html."""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent
players = json.loads((ROOT / "data" / "players.json").read_text())
tours = json.loads((ROOT / "data" / "tournaments.json").read_text())

# ship the whole field, but only the fields the card renders
KEEP = ("name", "pos", "total", "rounds", "amateur", "members")
for t in tours:
    t["leaderboard"] = [{k: r[k] for k in KEEP if k in r and r[k] not in (None, False)}
                        for r in t["leaderboard"]]

photos = sorted(p.stem for p in (ROOT / "img" / "course").glob("*.webp"))

blob = json.dumps({
    "players": players,
    "tournaments": tours,
    "captured": datetime.date.today().strftime("%-d %B %Y"),
}, separators=(",", ":"), ensure_ascii=False)

html = (ROOT / "template.html").read_text()
html = html.replace("/*__DATA__*/{players:[],tournaments:[]}", blob)
html = html.replace("/*__PHOTOS__*/[]", json.dumps(photos, separators=(",", ":")))
(ROOT / "index.html").write_text(html)

kb = (ROOT / "index.html").stat().st_size / 1024
print(f"index.html  {kb:,.0f} KB  ·  {len(players)} players + {len(tours)} tournaments + 4 charts "
      f"= {len(players) + len(tours) + 4} cards")
print(f"course photos: {len(photos)}/{len(tours)}")
