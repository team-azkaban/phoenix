from pathlib import Path

import rasterio
from rasterio.windows import from_bounds


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "population"
    / "worldpop"
    / "2024"
    / "ind_pop_2024_CN_100m_R2024B_v1.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "population"
    / "worldpop"
    / "2024"
    / "dahej"
)

OUTPUT_RASTER = OUTPUT_DIR / "dahej_population_2024_100m.tif"

WEST = 72.25
SOUTH = 21.35
EAST = 73.00
NORTH = 22.10


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(INPUT_RASTER) as src:
        if src.crs.to_string() != "EPSG:4326":
            raise ValueError(f"Expected EPSG:4326, got {src.crs}")

        window = from_bounds(
            WEST,
            SOUTH,
            EAST,
            NORTH,
            transform=src.transform,
        )

        # Round to whole pixels
        window = window.round_offsets().round_lengths()

        data = src.read(1, window=window)
        transform = src.window_transform(window)

        profile = src.profile.copy()
        profile.update(
            {
                "height": data.shape[0],
                "width": data.shape[1],
                "transform": transform,
                "compress": "deflate",
                "predictor": 2,
            }
        )

        with rasterio.open(OUTPUT_RASTER, "w", **profile) as dst:
            dst.write(data, 1)

        print("Population crop created successfully.")
        print(f"Output: {OUTPUT_RASTER}")
        print(f"Width: {data.shape[1]}")
        print(f"Height: {data.shape[0]}")
        print(f"Resolution: {src.res}")
        print(f"Bounds: {rasterio.transform.array_bounds(data.shape[0], data.shape[1], transform)}")
        print(f"Minimum: {data[data != src.nodata].min()}")
        print(f"Maximum: {data[data != src.nodata].max()}")


if __name__ == "__main__":
    main()