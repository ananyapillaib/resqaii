"""Download a small historical-weather sample from NASA POWER Daily API.

IMPORTANT: This queries one representative point only. It verifies Python/API
connectivity; it is NOT a spatial training dataset and is not enough to train
or validate a flood-risk model.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.json"
OUTPUT_DIR = ROOT / "data" / "raw" / "weather"
API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def main() -> int:
    settings = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    point = settings["weather_test_point"]
    weather = settings["historical_weather"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    params = {
        "latitude": point["latitude"],
        "longitude": point["longitude"],
        "start": weather["start_date"].replace("-", ""),
        "end": weather["end_date"].replace("-", ""),
        "parameters": ",".join(weather["parameters"]),
        "community": "RE",
        "format": "JSON",
        "time-standard": weather.get("time_standard", "UTC"),
    }

    print("Requesting historical daily weather from NASA POWER...")
    print(f"Point: {point['name']} ({point['latitude']}, {point['longitude']})")
    print(f"Date range: {weather['start_date']} to {weather['end_date']}")
    try:
        response = requests.get(API_URL, params=params, timeout=90)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        print(f"API request failed: {exc}")
        print("Check internet access and retry. If it persists, send Gigi the full error.")
        return 1
    except ValueError as exc:
        print(f"Response was not valid JSON: {exc}")
        return 1

    param_data = payload.get("properties", {}).get("parameter", {})
    if not param_data:
        print("No parameter data found. Response keys:", list(payload))
        print(json.dumps(payload, indent=2)[:3000])
        return 1

    date_keys = sorted(next(iter(param_data.values())).keys())
    df = pd.DataFrame({"date": pd.to_datetime(date_keys, format="%Y%m%d", errors="coerce")})
    for variable, values in param_data.items():
        df[variable] = [values.get(day) for day in date_keys]
    # NASA POWER uses -999 for missing/unavailable data in some products.
    df = df.mask(df == -999)

    if df.empty or df["date"].isna().all():
        print("No valid daily rows were returned.")
        return 1

    csv_path = OUTPUT_DIR / "wayanad_reference_point_daily_weather_2018_2025.csv"
    metadata_path = OUTPUT_DIR / "wayanad_reference_point_daily_weather_2018_2025.metadata.json"
    df.to_csv(csv_path, index=False)

    metadata = {
        "source": "NASA POWER Daily API",
        "api_url": API_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_parameters": params,
        "response_metadata": {
            "geometry": payload.get("geometry"),
            "header": payload.get("header"),
            "messages": payload.get("messages"),
            "parameters": payload.get("parameters"),
        },
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "warning": (
            "Single representative point only. Do not use as spatially complete training data. "
            "Check NASA POWER data provenance, spatial resolution, parameter units and applicable "
            "terms before modelling or publication."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")

    print("\nDownload successful.")
    print(f"Rows: {len(df)}")
    print(f"CSV: {csv_path}")
    print(f"Metadata: {metadata_path}")
    print("\nPreview:")
    print(df.head(5).to_string(index=False))
    print("\nReminder: this verifies API access only; next we need spatial data and defensible flood labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
