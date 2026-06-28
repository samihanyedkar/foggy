# Foggy — Build Guide

A step-by-step guide to building a real-time, neighborhood-level fog map of San Francisco — written for someone building their first app. Each phase ends with something you can actually see, so you're never building blind.

## The big idea

A real-time fog map is mostly a **data problem**, and only secondarily an app. Once you reliably know "how foggy is each part of the city right now," drawing it on a map is the easy part.

The whole system is a small loop:

> **fetch** weather for points around the city → **score** how foggy each point is → **save** to a file → **draw** the file on a map → repeat every few minutes.

That's it. Everything below is just filling in that loop and making it nicer.

## What's already in this folder

```
Foggy/
├── index.html              ← the map (open this to see it)
├── BUILD_GUIDE.md          ← you are here
└── data/
    ├── neighborhoods.json   ← the ~23 points we sample around SF
    ├── fetch_fog.py         ← the script that fetches weather + writes fog.json
    └── fog.json             ← the data the map reads (currently SAMPLE data)
```

The map already works using **sample data** so you can see the end result immediately. Phase 1 below swaps the sample for live weather.

## See it right now (2 minutes)

Browsers block pages from reading local files directly, so you run a tiny local
web server. In a terminal, from inside this folder:

```bash
cd "Foggy"
python3 -m http.server 8000
```

Then open **http://localhost:8000** in your browser. You should see SF with a blue fog blanket over the western/coastal neighborhoods and clear skies to the east — the classic summer-morning pattern. Click any dot to see its numbers.

(That blanket is the "smooth coverage map" you wanted — it's a *heatmap* MapLibre draws by blending the point scores. More on upgrading it in Phase 3.)

---

## The data sources we verified

| Source | What it gives | Cost | When we use it |
|---|---|---|---|
| **Open-Meteo** | Visibility, cloud cover, humidity, dew point at *any* lat/lon | Free, no key, 10k calls/day | **Phase 1 (now)** |
| **NWS Aviation Weather** (`aviationweather.gov/api/data/metar`) | Real airport-sensor visibility + cloud ceiling (SFO, OAK, HAF) | Free | Phase 4 (ground truth) |
| **GOES-18 satellite** (NOAA STAR, Pacific Southwest sector) | The actual marine-layer blanket from space; at night blue = fog | Free | Phase 5 (backdrop) |

One honest caveat about Open-Meteo: it returns *weather-model* output interpolated to a point, not raw sensor readings. It's perfect for learning and looks right most of the time, but it's already smoothed — so nearby points won't disagree as sharply as real microclimates do. That's exactly why Phase 4 mixes in real airport sensors.

---

## Phase 1 — Make the data real

**Goal:** replace the sample `fog.json` with live weather you fetched yourself.

You'll need Python 3 (check with `python3 --version`; macOS has it).

1. From the `data/` folder, run:

   ```bash
   cd "Foggy/data"
   python3 fetch_fog.py
   ```

2. You'll see a little text bar chart print for each neighborhood, and `fog.json` will be overwritten with real data. Reload http://localhost:8000 — the map now shows *actual* current fog.

**What to read in `fetch_fog.py`:** open it and read top to bottom. The two functions worth understanding are `fetch_weather` (calls Open-Meteo for one point) and `fog_score` (turns weather into a 0–1 number). The comments explain every step.

**Understanding the fog score.** Visibility does 70% of the work — under 0.5 km is dense fog (score 1), over 10 km is clear (score 0), sliding linearly between. The other 30% is a "moisture" check: high humidity and a small gap between temperature and dew point both mean fog-friendly air. These weights are yours to tune — that's the most satisfying knob to play with once it's running.

**If something breaks:** the most common issue is no internet or a typo in a lat/lon. The script prints `ERROR` next to any point it couldn't fetch and keeps going, so one failure won't sink the run.

---

## Phase 2 — The map (already built, worth understanding)

`index.html` is the whole frontend. It's plain HTML + JavaScript with one library, **MapLibre GL** (free, open-source). Resist adding React or a framework — this app is small enough that vanilla JS keeps you closer to what's actually happening.

Read `index.html` top to bottom. The flow is: create the map → `fetch("data/fog.json")` → convert the points to GeoJSON → add a **heatmap layer** (the blanket) and a **circle layer** (clickable dots). The `setInterval(load, ...)` at the bottom re-reads the file every 10 minutes.

Things to try, to learn by poking:
- Change `heatmap-radius` numbers to make the blanket tighter or softer.
- Change the `heatmap-color` ramp to your own palette.
- Add `temperature` to the popup.

---

## Phase 3 — A smoother, smarter blanket (IDW)

The heatmap is a quick approximation. The "proper" way to fill space between points is **Inverse Distance Weighting (IDW)**: for any spot on the map, its fog value is a weighted average of nearby points, where closer points count more.

When you're ready, the upgrade is: build a fine grid of points over the city, compute an IDW fog value for each grid cell in JavaScript (it's ~15 lines), and color the grid. This gives you full control over how the blanket looks and behaves, independent of MapLibre's built-in heatmap. Keep the heatmap version working while you build this beside it.

---

## Phase 4 — Real sensors + "real-time" that runs itself

Two upgrades that make it feel legit:

**Ground truth.** Add the NWS Aviation Weather API for SFO/OAK/HAF. These are real instruments measuring visibility and cloud ceiling. Use them to correct the model data near those airports (e.g. blend, or trust the sensor within a few km). Note the API wants a custom `User-Agent` header and allows 100 requests/minute.

**Automation.** Right now *you* run `fetch_fog.py`. To make it truly live without a server to babysit, use a **GitHub Action** on a schedule (every 10 minutes): it runs the script, commits the new `fog.json`, and — if you host the page with GitHub Pages — your live map updates on its own. This is the cheapest possible "always-on" setup (free) and a great thing to learn.

---

## Phase 5 — Satellite backdrop & polish

- **GOES-18 backdrop:** overlay the NOAA STAR GeoColor / Night Microphysics image for the Pacific Southwest sector as a faint layer under your points, so users see the real marine layer offshore rolling in. (Daytime needs a fog-specific product; at night GeoColor shows fog as blue.)
- **Time slider:** save each `fog.json` with a timestamp and let users scrub the last few hours to *watch* fog burn off and return.
- **Make it installable:** turn the page into a PWA so it can be "added to home screen" and feel like a phone app — no app store needed.

---

## How to host it (when ready to share)

The simplest path, free and beginner-friendly: push this folder to a **GitHub** repo and turn on **GitHub Pages**. Your map gets a public URL, and the GitHub Action from Phase 4 keeps the data fresh. No servers, no bills.

---

## Glossary

- **API** — a way for your code to ask another service (like Open-Meteo) for data over the internet.
- **JSON** — a simple text format for structured data; both `neighborhoods.json` and `fog.json` are JSON.
- **GeoJSON** — JSON with a specific shape that maps understand (points, lines, shapes with coordinates).
- **Heatmap** — a map layer that blends point values into a smooth colored gradient.
- **IDW (Inverse Distance Weighting)** — a way to estimate a value anywhere by averaging nearby known values, weighted by closeness.
- **METAR** — the standardized airport weather report format (where the real sensor data comes from).
- **PWA (Progressive Web App)** — a website that can be installed and behaves like a native app.

## Suggested order to learn in

1. Get the map showing with sample data (done — just run the server).
2. Run `fetch_fog.py`; read it until every line makes sense.
3. Tune the fog score weights and watch the map change.
4. Read `index.html`; change the colors and radius.
5. Automate with a GitHub Action.
6. Then reach for IDW, real sensors, and the satellite layer.

Build one phase at a time. Each is a real, finished thing on its own.
