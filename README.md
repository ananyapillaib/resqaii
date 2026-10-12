# ResQAI — implementation starter

ResQAI is being built as a staged AI-driven disaster prediction and decision-support system. The first prototype focuses on **flood risk/susceptibility for Wayanad, Kerala**. Landslide prediction, synthetic-data generation, multi-agent response, route/shelter recommendations, and the Flutter app remain later stages until the first flood pipeline is validated.

## Important modelling boundary

The first script downloads historical weather for one representative point only to verify that the Python environment and NASA POWER API work. It is **not** a spatial training dataset and must not be presented as a flood-prediction model. Before training, we must obtain a defensible historical flood inventory/extent, define the label construction procedure, align raster features and create a spatially appropriate train/test split.

## Project folders

- `data/raw/`: original downloads; keep these unchanged.
- `data/processed/`: clipped/aligned/cleaned geospatial layers.
- `data/final_dataset/`: feature table or raster stack used for training.
- `scripts/`: repeatable Python scripts.
- `notebooks/`: exploratory analysis only; move reusable steps into scripts.
- `models/`: saved trained models.
- `outputs/`: maps, graphs, reports and evaluation results.
- `docs/data_inventory_template.csv`: record source, date, resolution, CRS, licence and quality notes for every input.

## Setup (Windows PowerShell)

Open this folder in VS Code, then open **Terminal → New Terminal**.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/check_environment.py
```

If PowerShell blocks environment activation, run this in that terminal and try activating again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If `py -3.12` is not recognized, run `python --version`. Use the Python version already installed and tell us what it prints if setup fails.

## First task: verify historical weather access (NASA POWER)

```powershell
python scripts/fetch_historical_weather.py
python scripts/inspect_weather.py
```

The script saves a CSV and a metadata JSON in `data/raw/weather/`. It uses NASA POWER Daily API for a representative Wayanad coordinate configured in `config/settings.json` and a fixed historical period (2018–2025) for repeatability. NASA POWER provides free, global historical meteorological data; review its spatial resolution and parameter units before modelling. Treat this as an **API smoke test only**. Once it runs, we will download the study-area boundary and elevation data, then plan the spatial flood labels.

## Data sources named in the project plan

- Historical daily weather (first prototype): NASA POWER Daily API. Current conditions and forecast: Open-Meteo Forecast API (add after the baseline data pipeline is established).
- Elevation: SRTM 30 m or Copernicus DEM.
- Terrain: derived from the DEM (e.g. slope, aspect, roughness).
- Historical flood records/extent: KSDMA, NDMA, government reports and/or a validated satellite-derived flood extent.
- Land cover: ESA WorldCover and/or Sentinel-2.
- Road network: OpenStreetMap.
- Shelters: official Kerala/district records or verified field/administrative sources.

These are proposed sources from the project plan, not a claim that all required data are already available or that every source provides a machine-readable dataset. Verify each file's coverage, date, coordinate system, resolution, licence and usefulness before modelling.

## Planned first prototype

1. Establish environment and confirm an API call.
2. Obtain Wayanad district boundary.
3. Obtain a DEM and derive terrain features.
4. Obtain/derive a historical flood inventory or satellite flood-extent mask.
5. Build and audit a spatial feature/label dataset.
6. Train a simple baseline and evaluate on spatially held-out data.
7. Make a risk/susceptibility map and validate it against independent observations.
8. Add historical/forecast rainfall effects only after the time and label alignment is clear.

Do not generate synthetic training labels or report performance metrics before the real labels and evaluation design are defensible.
