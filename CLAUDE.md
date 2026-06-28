# CLAUDE.md — Foggy

Context for Claude Code working in this repo. Read this first.

## What this project is

A real-time, neighborhood-level fog map of San Francisco. SF has dramatic
microclimates — coastal/western neighborhoods can be socked in fog while the
eastern/interior ones are sunny, and it shifts hour to hour as fog burns off
and returns. This app visualizes that live.

## Who's building it

A first-time app builder. **Optimize explanations for learning** — explain *why*,
not just *what*; prefer simple, readable code over clever code; introduce one new
concept at a time. Avoid adding frameworks or tooling unless there's a clear reason.

## The core loop

> fetch weather for points around the city → score each point's fogginess (0–1)
> → save to `data/fog.json` → the map reads that file and draws it → repeat.

`data/fog.json` is the single contract between the data side and the map side.

## File map

```
Foggy/
├── index.html              # The whole frontend: MapLibre GL map + heatmap + clickable dots.
├── BUILD_GUIDE.md          # The 5-phase plan, written for the user. Source of truth for direction.
├── CLAUDE.md               # This file.
└── data/
    ├── neighborhoods.json   # ~23 SF sample points (id, name, lat, lon).
    ├── fetch_fog.py         # Fetches Open-Meteo weather per point, computes fog_score, writes fog.json.
    └── fog.json             # Latest output. Currently real Open-Meteo data.
```

## How to run

```bash
# Refresh the data (no API key needed):
cd data && python3 fetch_fog.py

# Serve the map (browsers block file:// fetches, so a server is required):
python3 -m http.server 8000   # from the project root, then open http://localhost:8000
```

## Tech decisions (and why)

- **Web app, vanilla HTML/JS** — simplest cross-platform path; no framework so the
  user stays close to fundamentals. Don't introduce React unless it earns its place.
- **MapLibre GL JS** (CDN) — free, no API key. The fog "blanket" is a MapLibre
  heatmap layer weighted by `fog_score`. Basemap is CARTO Positron raster tiles (no key).
- **Open-Meteo** — free, no key, any lat/lon. Provides visibility, cloud cover,
  humidity, dew point. Caveat: it's *model* output interpolated to a point, not raw
  sensors, so it's pre-smoothed. Phase 4 adds real airport sensors to sharpen contrast.
- **No backend yet** — a static page reading a JSON file. "Real-time" comes from
  re-running the fetch (Phase 4: a GitHub Action on a schedule), not a live server.

## The fog score (in fetch_fog.py)

`fog_score` is 0.0 (clear) to 1.0 (socked in):
- 70% from visibility: ≤0.5 km → 1, ≥10 km → 0, linear between.
- 30% from moisture: high humidity + small temperature/dew-point gap → foggier.
These weights are intentionally simple and meant to be tuned. If you change the
formula, keep it readable and explain the reasoning to the user.

## Roadmap (see BUILD_GUIDE.md for detail)

1. **Data real** — run fetch_fog.py for live data. ✅ done (fog.json is live Open-Meteo).
2. **Map** — index.html renders the heatmap + dots. ✅ done.
3. **Smoother blanket** — replace heatmap approximation with explicit IDW over a grid.
4. **Real sensors + automation** — add NWS Aviation Weather (SFO/OAK/HAF METARs) for
   ground truth; automate fetch via a scheduled GitHub Action; host on GitHub Pages.
5. **Polish** — GOES-18 satellite backdrop, time slider to scrub recent hours, PWA install.

## Verified data sources

- Open-Meteo: https://open-meteo.com/en/docs (visibility in meters; free, 10k calls/day)
- NWS Aviation Weather Data API: https://aviationweather.gov/data/api/
  (`/api/data/metar?ids=KSFO,KOAK,KHAF&format=json`; wants a custom User-Agent; 100 req/min)
- GOES-18 GeoColor, Pacific Southwest sector (NOAA STAR): night = blue is fog.

## Conventions

- Keep `data/fog.json` as the only thing the map reads — don't have index.html call
  weather APIs directly (keeps the data logic in one place).
- Lat/lon order: GeoJSON and MapLibre use **[lon, lat]**; neighborhoods.json stores
  them as separate `lat`/`lon` fields. Mind the order when converting.
- No secrets in this repo (none needed — all sources are keyless so far).

## Next likely task

Set up a GitHub Action to run `fetch_fog.py` every ~10 min and commit `fog.json`,
plus GitHub Pages hosting. That makes the map self-updating and publicly shareable.
