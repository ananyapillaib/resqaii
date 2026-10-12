from pathlib import Path
import json

import numpy as np
import rasterio

from rasterio.warp import (
    calculate_default_transform,
    reproject,
    Resampling,
)

ROOT = Path(__file__).resolve().parents[1]

INPUT_DEM = (
    ROOT / "data" / "raw" / "dem"
    / "wayanad_dem_90m.tif"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "terrain"

PROJECTED_DEM = OUTPUT_DIR / "wayanad_dem_utm43n_90m.tif"
SLOPE_FILE = OUTPUT_DIR / "wayanad_slope_degrees.tif"

TARGET_CRS = "EPSG:32643"
NODATA = -9999.0


def main():
    if not INPUT_DEM.exists():
        raise FileNotFoundError(
            f"DEM not found: {INPUT_DEM}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Step 1: Reading elevation data...")

    with rasterio.open(INPUT_DEM) as src:
        if src.crs is None:
            raise ValueError("Input DEM has no CRS.")

        source = src.read(1).astype(np.float32)
        source_nodata = (
            src.nodata if src.nodata is not None else NODATA
        )

        transform, width, height = calculate_default_transform(
            src.crs,
            TARGET_CRS,
            src.width,
            src.height,
            *src.bounds,
            resolution=90,
        )

        destination = np.full(
            (height, width), NODATA, dtype=np.float32
        )

        reproject(
            source=source,
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=source_nodata,
            dst_transform=transform,
            dst_crs=TARGET_CRS,
            dst_nodata=NODATA,
            resampling=Resampling.bilinear,
        )

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": TARGET_CRS,
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
    }

    with rasterio.open(
        PROJECTED_DEM, "w", **profile
    ) as dst:
        dst.write(destination, 1)

    print("Projected DEM saved:", PROJECTED_DEM)
    print("Step 2: Calculating slope...")

    with rasterio.open(PROJECTED_DEM) as src:
        elevation = src.read(1).astype(np.float64)

        valid = (
            np.isfinite(elevation)
            & (elevation != NODATA)
        )

        elevation[~valid] = np.nan

        pixel_y = abs(src.transform.e)
        pixel_x = abs(src.transform.a)

        dz_dy, dz_dx = np.gradient(
            elevation, pixel_y, pixel_x
        )

        slope = np.degrees(
            np.arctan(np.hypot(dz_dx, dz_dy))
        )

        slope[~np.isfinite(slope)] = NODATA

        slope_profile = src.profile.copy()
        slope_profile.update(
            dtype="float32",
            nodata=NODATA,
            compress="deflate",
        )

        with rasterio.open(
            SLOPE_FILE, "w", **slope_profile
        ) as dst:
            dst.write(slope.astype(np.float32), 1)

    with rasterio.open(SLOPE_FILE) as src:
        result = src.read(1, masked=True)
        valid_values = result.compressed()

        if valid_values.size == 0:
            raise ValueError("No valid slope pixels were produced.")

        print("\nSUCCESS!")
        print("Slope raster:", SLOPE_FILE)
        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Valid slope pixels:", valid_values.size)
        print("Minimum slope (degrees):", round(float(valid_values.min()), 2))
        print("Maximum slope (degrees):", round(float(valid_values.max()), 2))

    metadata = {
        "study_area": "Wayanad, Kerala, India",
        "input_dem": str(INPUT_DEM),
        "projected_crs": TARGET_CRS,
        "slope_units": "degrees",
        "method": "Slope calculated from elevation gradients",
        "slope_output": str(SLOPE_FILE),
    }

    metadata_file = OUTPUT_DIR / "terrain_metadata.json"
    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()