from pathlib import Path
import math
import json
import requests
import geopandas as gpd
import rasterio

from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile
from shapely.geometry import mapping
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[1]

BOUNDARY_FILE = (
    ROOT / "data" / "raw" / "boundaries"
    / "wayanad_boundary.geojson"
)

DEM_DIR = ROOT / "data" / "raw" / "dem"
TILE_DIR = DEM_DIR / "tiles"
OUTPUT_FILE = DEM_DIR / "wayanad_dem_90m.tif"

BASE_URL = (
    "https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com"
)


def tile_name(lat, lon):
    lat_code = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_code = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"

    return (
        f"Copernicus_DSM_COG_30_{lat_code}_00_"
        f"{lon_code}_00_DEM"
    )


def main():
    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(
            "Wayanad boundary is missing. First run:\n"
            "python scripts/download_wayanad_boundary.py"
        )

    DEM_DIR.mkdir(parents=True, exist_ok=True)
    TILE_DIR.mkdir(parents=True, exist_ok=True)

    boundary = gpd.read_file(BOUNDARY_FILE)

    if boundary.empty:
        raise ValueError("The Wayanad boundary file is empty.")

    boundary = boundary.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = boundary.total_bounds

    print("Wayanad boundary loaded.")
    print("Finding elevation tiles...")

    tile_paths = []

    for lat in range(math.floor(miny), math.floor(maxy) + 1):
        for lon in range(math.floor(minx), math.floor(maxx) + 1):
            name = tile_name(lat, lon)
            tile_path = TILE_DIR / f"{name}.tif"

            url = f"{BASE_URL}/{name}/{name}.tif"

            if not tile_path.exists():
                print("Requesting:", name)

                response = requests.get(
                    url, stream=True, timeout=180
                )

                if response.status_code == 404:
                    response.close()
                    print("Tile not available:", name)
                    continue

                response.raise_for_status()

                temporary = tile_path.with_suffix(".part")

                try:
                    with open(temporary, "wb") as f:
                        for chunk in response.iter_content(
                            chunk_size=1024 * 1024
                        ):
                            if chunk:
                                f.write(chunk)

                    temporary.replace(tile_path)

                finally:
                    response.close()
                    if temporary.exists():
                        temporary.unlink()

            # Check that the tile is a readable raster.
            with rasterio.open(tile_path) as src:
                if src.crs is None:
                    raise ValueError(f"Tile has no CRS: {name}")

            tile_paths.append(tile_path)

    if not tile_paths:
        raise RuntimeError(
            "No elevation tiles were downloaded. "
            "Check the network and tile URLs."
        )

    print(f"Found {len(tile_paths)} elevation tile(s).")
    print("Combining tiles...")

    with ExitStack() as stack:
        sources = [
            stack.enter_context(rasterio.open(path))
            for path in tile_paths
        ]

        mosaic, transform = merge(sources)

        profile = sources[0].profile.copy()
        profile.update(
            driver="GTiff",
            height=mosaic.shape[1],
            width=mosaic.shape[2],
            count=mosaic.shape[0],
            transform=transform,
            compress="deflate",
        )

        boundary_projected = boundary.to_crs(sources[0].crs)
        geometries = [
            mapping(geom)
            for geom in boundary_projected.geometry
            if geom is not None
        ]

        if not geometries:
            raise ValueError("No valid boundary geometry found.")

        print("Clipping elevation data to Wayanad...")

        with MemoryFile() as memory_file:
            with memory_file.open(**profile) as merged_raster:
                merged_raster.write(mosaic)

                nodata = (
                    merged_raster.nodata
                    if merged_raster.nodata is not None
                    else -9999
                )

                clipped, clipped_transform = mask(
                    merged_raster,
                    geometries,
                    crop=True,
                    nodata=nodata,
                )

                output_profile = profile.copy()
                output_profile.update(
                    height=clipped.shape[1],
                    width=clipped.shape[2],
                    transform=clipped_transform,
                    nodata=nodata,
                )

                with rasterio.open(
                    OUTPUT_FILE, "w", **output_profile
                ) as output:
                    output.write(clipped)

    metadata = {
        "dataset": "Copernicus DEM GLO-90",
        "type": "Digital Surface Model",
        "study_area": "Wayanad, Kerala, India",
        "nominal_resolution": "90 metres",
        "source": BASE_URL,
        "output": str(OUTPUT_FILE),
    }

    metadata_path = DEM_DIR / "wayanad_dem_90m.metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    with rasterio.open(OUTPUT_FILE) as result:
        print("\nSUCCESS!")
        print("Output:", OUTPUT_FILE)
        print("CRS:", result.crs)
        print("Dimensions:", result.width, "x", result.height)
        print("Resolution:", result.res)

    print("Metadata:", metadata_path)


if __name__ == "__main__":
    main()