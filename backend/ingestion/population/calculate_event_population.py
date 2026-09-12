from pathlib import Path
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window


PROJECT_ROOT = Path(__file__).resolve().parents[3]

POPULATION_RASTER = (
    PROJECT_ROOT
    / "data"
    / "population"
    / "worldpop"
    / "2024"
    / "dahej"
    / "dahej_population_2024_100m.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "population"
    / "processed"
)

OUTPUT_CSV = OUTPUT_DIR / "dahej_event_population_2024.csv"

# Population exposure radius around each thermal event.
RADIUS_M = 250.0

# Earth's radius in metres.
EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between two latitude/longitude points.
    Returns distance in metres.
    """
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def load_events():
    """
    Load thermal events from Supabase using the existing project
    database connection.
    """
    import sys

    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

    from db.database import SessionLocal
    from db.models.thermal_event import ThermalEvent

    db = SessionLocal()

    try:
        events = (
            db.query(
                ThermalEvent.event_id,
                ThermalEvent.latitude,
                ThermalEvent.longitude,
                ThermalEvent.first_seen,
            )
            .filter(
                ThermalEvent.latitude.isnot(None),
                ThermalEvent.longitude.isnot(None),
            )
            .order_by(ThermalEvent.first_seen)
            .all()
        )

        return events

    finally:
        db.close()


def population_within_radius(
    src,
    latitude,
    longitude,
    radius_m,
):
    """
    Calculate total WorldPop population within radius_m of an event.

    WorldPop values represent population counts per raster pixel.
    Pixels whose centres fall within the radius are summed.
    """

    # Approximate latitude/longitude extent corresponding to radius.
    lat_delta = radius_m / 111_320.0

    cos_lat = max(
        math.cos(math.radians(latitude)),
        0.01,
    )

    lon_delta = radius_m / (111_320.0 * cos_lat)

    min_lon = longitude - lon_delta
    max_lon = longitude + lon_delta
    min_lat = latitude - lat_delta
    max_lat = latitude + lat_delta

    window = rasterio.windows.from_bounds(
        min_lon,
        min_lat,
        max_lon,
        max_lat,
        transform=src.transform,
    )

    window = window.round_offsets().round_lengths()

    # Keep the window inside the raster.
    full_window = Window(
        0,
        0,
        src.width,
        src.height,
    )

    window = window.intersection(full_window)

    if window.width <= 0 or window.height <= 0:
        return 0.0, 0

    data = src.read(
        1,
        window=window,
        masked=True,
    )

    height, width = data.shape

    # Window transform.
    transform = src.window_transform(window)

    # Build row/column arrays.
    rows = np.arange(height)
    cols = np.arange(width)

    row_grid, col_grid = np.meshgrid(
        rows,
        cols,
        indexing="ij",
    )

    # Calculate pixel-centre longitude/latitude directly.
    xs = (
        transform.c
        + (col_grid + 0.5) * transform.a
    )

    ys = (
        transform.f
        + (row_grid + 0.5) * transform.e
    )

    # Haversine distance from event to every pixel centre.
    lat1 = math.radians(latitude)

    lat2 = np.radians(ys)

    dlat = lat2 - lat1
    dlon = np.radians(xs - longitude)

    a = (
        np.sin(dlat / 2.0) ** 2
        + math.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2.0) ** 2
    )

    distances = (
        2.0
        * EARTH_RADIUS_M
        * np.arcsin(
            np.sqrt(a)
        )
    )

    # Force mask to exactly the same shape as data.
    mask = np.ma.getmaskarray(data)

    valid = (
        (~mask)
        & np.isfinite(data.data)
        & (data.data >= 0)
        & (distances <= radius_m)
    )

    if not np.any(valid):
        return 0.0, 0

    population = float(
        np.sum(data.data[valid])
    )

    pixel_count = int(
        np.sum(valid)
    )

    return population, pixel_count


def main():
    print("=" * 70)
    print("PHOENIX - EVENT POPULATION EXPOSURE")
    print("=" * 70)

    if not POPULATION_RASTER.exists():
        raise FileNotFoundError(
            f"Population raster not found:\n{POPULATION_RASTER}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"\nPopulation raster:")
    print(POPULATION_RASTER)

    print(f"\nExposure radius: {RADIUS_M:.0f} m")

    events = load_events()

    print(f"\nThermal events found: {len(events)}")

    if not events:
        raise RuntimeError(
            "No thermal events found in Supabase."
        )

    results = []

    with rasterio.open(POPULATION_RASTER) as src:

        print("\nRaster information:")
        print(f"  CRS: {src.crs}")
        print(f"  Resolution: {src.res}")
        print(f"  Width: {src.width}")
        print(f"  Height: {src.height}")
        print(f"  Bounds: {src.bounds}")
        print(f"  NoData: {src.nodata}")

        for index, event in enumerate(events, start=1):

            event_id = str(event.event_id)
            latitude = float(event.latitude)
            longitude = float(event.longitude)

            population, pixel_count = population_within_radius(
                src=src,
                latitude=latitude,
                longitude=longitude,
                radius_m=RADIUS_M,
            )

            results.append(
                {
                    "event_id": event_id,
                    "event_timestamp": event.first_seen,
                    "event_latitude": latitude,
                    "event_longitude": longitude,
                    "exposure_radius_m": RADIUS_M,
                    "population_exposed": population,
                    "population_pixels": pixel_count,
                    "source": "WorldPop R2024B 100m constrained",
                }
            )

            if index % 250 == 0:
                print(
                    f"  Processed {index}/{len(events)} events"
                )

    df = pd.DataFrame(results)

    # Basic validation.
    if df["event_id"].duplicated().any():
        duplicates = df[df["event_id"].duplicated()]["event_id"].tolist()
        raise ValueError(
            f"Duplicate event IDs found: {duplicates[:10]}"
        )

    if len(df) != len(events):
        raise ValueError(
            "Output row count does not match event count."
        )

    if df["population_exposed"].isna().any():
        raise ValueError(
            "Some events have missing population exposure."
        )

    if (df["population_exposed"] < 0).any():
        raise ValueError(
            "Negative population exposure detected."
        )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print("\n" + "=" * 70)
    print("POPULATION PROCESSING COMPLETE")
    print("=" * 70)

    print(f"\nOutput:")
    print(OUTPUT_CSV)

    print("\nRecords:")
    print(f"  Events processed: {len(df)}")
    print(
        f"  Events with population > 0: "
        f"{(df['population_exposed'] > 0).sum()}"
    )
    print(
        f"  Events with population = 0: "
        f"{(df['population_exposed'] == 0).sum()}"
    )

    print("\nPopulation exposure statistics:")
    print(
        f"  Minimum: {df['population_exposed'].min():.2f}"
    )
    print(
        f"  Median: {df['population_exposed'].median():.2f}"
    )
    print(
        f"  Mean: {df['population_exposed'].mean():.2f}"
    )
    print(
        f"  Maximum: {df['population_exposed'].max():.2f}"
    )

    print("\nPixel statistics:")
    print(
        f"  Minimum pixels: {df['population_pixels'].min()}"
    )
    print(
        f"  Median pixels: {df['population_pixels'].median():.0f}"
    )
    print(
        f"  Maximum pixels: {df['population_pixels'].max()}"
    )

    print("\n✓ CSV created successfully.")
    print("✓ No Supabase records were modified.")


if __name__ == "__main__":
    main()