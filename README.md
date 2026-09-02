# PGA TOUR 2026 — Season Film

An interactive card film of the 2026 PGA TOUR season: the **FedExCup top 70** in season-points
order, then all **37 tournaments** of the FedExCup season in calendar order, then two chart cards.
109 cards, one screen each.

Live: https://golf.aguywithascarf.com
Part of the AGWAS family at https://dataviz.aguywithascarf.com

## Card order — an editorial choice

Cards run in **FedExCup points** order, rebuilt by summing each player's per-event points across the
season. This is deliberately *not* the Tour's published final standings: since the staggered start
was dropped, those rank the top 30 by finishing position at the TOUR Championship.

| | 1 | 2 | 3 |
|---|---|---|---|
| Published final standings (East Lake finish) | Scheffler | Hovland | Gerard |
| **Season points — used here** | **Scheffler** | **Fitzpatrick** | **Clark** |

The TOUR Championship awards no FedExCup points, so the points list is settled after the BMW
Championship.

## Data

Everything is scraped from server-rendered `__NEXT_DATA__` on pgatour.com — plain `curl`, no
Cloudflare challenge, no API key.

| What | Where |
|---|---|
| Standings (219 players) | `/fedexcup/official-standings.html` → `tourCupMetaList[0].officialPlayers` |
| Per-player season results **incl. FedExCup points per event** | `/player/{id}/x/results` → query `playerProfileResults` |
| Schedule, courses, purses, champions, logos, course photos | `/schedule` → query `schedule` |
| Event leaderboards | `/tournaments/2026/x/{tid}/leaderboard` → query `leaderboard` |
| World ranking | `https://apiweb.owgr.com/api/owgr/rankings/getRankings?pageSize=600&...` |

### Gotchas worth remembering

- The **slug segment is required** for player and tournament tab routing. `/player/46046/results`
  silently serves the *overview* page; `/player/46046/x/results` serves the results tab.
- The Zurich Classic is a **two-man team** event and uses `teamStrokePlayLeaderboard`, not
  `leaderboard`. Its schedule entry carries two `champions`.
- Player images are `headshots_{id}` on `pga-tour-res.cloudinary.com` — **head-and-shoulders cutouts
  only**, there is no full-body "gladiator" equivalent as on atptour.com.
- Tournament logos live on a different host: `res.cloudinary.com/pgatour-prod/image/upload/{path}.png`.
- **11 of 37 events have no course photo** on the CDN at any hole number; those cards fall back to a
  gradient ground plus the logo.
- OWGR leaves `iocCode` blank for UK home nations — use the PGA TOUR flag (it gives ENG/SCO/NIR).
- OWGR uses formal first names (Nicolas Echavarria, Samuel Stevens) where the Tour uses familiar
  ones, so matching falls back to surname + first initial.

## Rebuild

```
python3 tools/fetch.py base          # standings + schedule + OWGR
python3 tools/fetch.py players 90    # per-player result pages (cached on disk)
python3 tools/fetch.py tournaments   # 37 leaderboards
python3 tools/build_points.py        # sum per-event points -> points_list.json
python3 tools/build_players.py       # top 70 + bio + OWGR -> players.json
python3 tools/build_tournaments.py   # schedule + leaderboards -> tournaments.json
python3 tools/fetch_images.py        # portraits, faces, logos, course photos
python3 render.py                    # template.html + data -> index.html
```

Raw pages cache in `scratch/raw/` — delete a file to refetch it.

## Deploy

GitHub Pages from `main` / root. `CNAME` + `.nojekyll` are committed. `scratch/` is gitignored.
