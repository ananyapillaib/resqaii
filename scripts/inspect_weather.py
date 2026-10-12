"""Quick data-quality inspection for the weather API test file."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "weather" / "wayanad_reference_point_daily_weather_2018_2025.csv"


def main() -> int:
    if not CSV_PATH.exists():
        print("Weather CSV not found. Run: python scripts/fetch_historical_weather.py")
        return 1

    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    print("Shape (rows, columns):", df.shape)
    print("Date range:", df["date"].min(), "to", df["date"].max())
    print("Columns:", list(df.columns))
    print("\nMissing values by column:\n", df.isna().sum().to_string())
    print("\nNumerical summary:\n", df.select_dtypes(include="number").describe().round(2).to_string())
    rainfall_column = "PRECTOTCORR"
    if rainfall_column in df.columns:
        print("\nTen wettest dates in this point series:")
        print(df.nlargest(10, rainfall_column)[["date", rainfall_column]].to_string(index=False))

    print("\nThis is one point's weather series, not flood labels or a district-wide dataset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
