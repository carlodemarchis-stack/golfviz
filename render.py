"""Inject the built datasets into template.html -> index.html."""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent
players = json.loads((ROOT / "data" / "players.json").read_text())
tours = json.loads((ROOT / "data" / "tournaments.json").read_text())

# only ship the leaderboard rows the card actually renders
for t in tours:
    t["leaderboard"] = t["leaderboard"][:22]

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
print(f"index.html  {kb:,.0f} KB  ·  {len(players)} players + {len(tours)} tournaments + 3 charts "
      f"= {len(players) + len(tours) + 3} cards")
print(f"course photos: {len(photos)}/{len(tours)}")
