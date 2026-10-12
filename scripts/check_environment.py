"""Check whether the packages needed for the ResQAI starter are importable."""
from importlib import import_module
import sys

MODULES = [
    "pandas", "numpy", "requests", "sklearn", "matplotlib",
    "geopandas", "rasterio", "shapely", "pyproj", "folium", "joblib"
]


def main() -> int:
    failed = []
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}\n")
    for module in MODULES:
        try:
            loaded = import_module(module)
            version = getattr(loaded, "__version__", "version unknown")
            print(f"OK   {module}: {version}")
        except Exception as exc:  # report package import errors rather than hide them
            failed.append((module, str(exc)))
            print(f"FAIL {module}: {exc}")

    if failed:
        print("\nSome packages failed to import. Copy the full error output and send it to Gigi.")
        return 1
    print("\nEnvironment check passed. Next run scripts/fetch_historical_weather.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
