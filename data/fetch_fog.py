"""
SF Fog Map — Phase 1: the data pipeline.

What this script does, end to end:
  1. Reads the list of neighborhood points from neighborhoods.json
  2. Asks Open-Meteo for current weather at each point (free, no API key)
  3. Turns each point's weather into a single "fog score" from 0.0 to 1.0
  4. Writes everything to fog.json

That fog.json file is the ONE thing the map (Phase 2) will read.
Run it with:   python3 fetch_fog.py

Nothing here needs an account or a key. If you can browse the web, this runs.
"""

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

# Where this script lives, so paths work no matter where you run it from.
HERE = Path(__file__).parent
NEIGHBORHOODS_FILE = HERE / "neighborhoods.json"
OUTPUT_FILE = HERE / "fog.json"

# The weather fields we ask Open-Meteo for. Each one is a clue about fog.
CURRENT_FIELDS = [
    "visibility",            # meters you can see — the single best fog signal
    "cloud_cover",           # % of sky covered by cloud
    "relative_humidity_2m",  # % humidity; fog needs very moist air
    "temperature_2m",        # air temp in C
    "dew_point_2m",          # temp at which air saturates; fog forms when temp ~ dew point
]


def fetch_weather(lat, lon):
    """Ask Open-Meteo for current conditions at one lat/lon. Returns a dict."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(CURRENT_FIELDS),
        "timezone": "America/Los_Angeles",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    # A User-Agent is polite and avoids being filtered as an anonymous bot.
    req = Request(url, headers={"User-Agent": "foggy/0.1"})
    with urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    return data["current"]


def fog_score(weather):
    """
    Turn raw weather into a 0.0 (clear) to 1.0 (socked in) fog score.

    The logic, in plain English:
      - Visibility is the strongest signal. Under ~0.5 km is dense fog (score 1).
        Over ~10 km is clear (score 0). In between we slide linearly.
      - We then nudge that up when the air is saturated: high humidity AND a
        small gap between temperature and dew point both mean fog-friendly air.

    Visibility does most of the work (weight 0.7); the moisture check refines it
    (weight 0.3). These weights are yours to tune later — that's the fun part.
    """
    vis_m = weather.get("visibility")
    rh = weather.get("relative_humidity_2m")
    temp = weather.get("temperature_2m")
    dew = weather.get("dew_point_2m")

    # --- Visibility component ---
    if vis_m is None:
        vis_component = 0.0
    else:
        vis_km = vis_m / 1000.0
        if vis_km <= 0.5:
            vis_component = 1.0
        elif vis_km >= 10.0:
            vis_component = 0.0
        else:
            # Linear slide from 1.0 (at 0.5 km) down to 0.0 (at 10 km).
            vis_component = (10.0 - vis_km) / (10.0 - 0.5)

    # --- Moisture component ---
    # Humidity contribution: ramps from 0 at 80% RH to 1 at 100% RH.
    if rh is None:
        humidity_part = 0.0
    else:
        humidity_part = clamp((rh - 80.0) / 20.0, 0.0, 1.0)

    # Dew-point depression: how close temp is to the dew point.
    # 0 C gap = saturated (foggy); 4 C gap or more = dry air.
    if temp is None or dew is None:
        depression_part = 0.0
    else:
        depression = temp - dew
        depression_part = clamp((4.0 - depression) / 4.0, 0.0, 1.0)

    moisture_component = (humidity_part + depression_part) / 2.0

    score = 0.7 * vis_component + 0.3 * moisture_component
    return round(clamp(score, 0.0, 1.0), 3)


def clamp(value, low, high):
    """Keep a number inside [low, high]."""
    return max(low, min(high, value))


def main():
    neighborhoods = json.loads(NEIGHBORHOODS_FILE.read_text())
    print(f"Fetching fog data for {len(neighborhoods)} neighborhoods...\n")

    points = []
    for n in neighborhoods:
        try:
            weather = fetch_weather(n["lat"], n["lon"])
            score = fog_score(weather)
            points.append({
                "id": n["id"],
                "name": n["name"],
                "lat": n["lat"],
                "lon": n["lon"],
                "fog_score": score,
                "visibility_m": weather.get("visibility"),
                "cloud_cover": weather.get("cloud_cover"),
                "humidity": weather.get("relative_humidity_2m"),
                "temperature": weather.get("temperature_2m"),
                "dew_point": weather.get("dew_point_2m"),
            })
            bar = "#" * int(score * 20)
            print(f"  {n['name']:<20} fog {score:>5.2f}  {bar}")
            # Be a good citizen: small pause so we don't hammer the free API.
            time.sleep(0.2)
        except Exception as e:
            print(f"  {n['name']:<20} ERROR: {e}")

    output = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "open-meteo",
        "points": points,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {len(points)} points to {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
