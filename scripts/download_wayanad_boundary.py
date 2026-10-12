from pathlib import Path
import json
import requests
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]

URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/"
    "9469f09/releaseData/gbOpen/IND/ADM2/"
    "geoBoundaries-IND-ADM2_simplified.geojson"
)

OUTPUT_DIR = ROOT / "data" / "raw" / "boundaries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Downloading India district boundaries...")

    response = requests.get(URL, timeout=120)
    response.raise_for_status()
    data = response.json()

    districts = gpd.GeoDataFrame.from_features(
        data["features"],
        crs="EPSG:4326"
    )

    print("Available columns:", list(districts.columns))

    # Find the column containing district names.
    name_columns = [
        col for col in districts.columns
        if "name" in col.lower() or "district" in col.lower()
    ]

    if not name_columns:
        raise ValueError(
            "Could not identify a district-name column."
        )

    # Find Wayanad without depending on capitalization.
    mask = districts[name_columns].astype(str).apply(
        lambda col: col.str.contains(
            "Wayanad", case=False, na=False
        )
    ).any(axis=1)

    wayanad = districts[mask]

    if len(wayanad) != 1:
        print("Matching records:", len(wayanad))
        print(wayanad[name_columns].to_string(index=False))
        raise ValueError(
            "Expected exactly one Wayanad boundary."
        )

    output_file = OUTPUT_DIR / "wayanad_boundary.geojson"
    wayanad.to_file(output_file, driver="GeoJSON")

    metadata = {
        "source": "geoBoundaries",
        "country": "India",
        "administrative_level": "ADM2 - district",
        "district": "Wayanad",
        "source_url": URL,
        "reported_license": (
            "Open Data Commons Open Database License 1.0"
        )
    }

    metadata_file = (
        OUTPUT_DIR / "wayanad_boundary.metadata.json"
    )
    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8"
    )

    print("\nDownload successful!")
    print("District:", wayanad[name_columns].to_dict("records"))
    print("CRS:", wayanad.crs)
    print("Boundary:", output_file)
    print("Metadata:", metadata_file)


if __name__ == "__main__":
    main()