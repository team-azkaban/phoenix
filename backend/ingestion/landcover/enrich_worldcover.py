from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from sqlalchemy import text

from db.database import SessionLocal


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RASTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "landcover"
    / "worldcover"
    / "2021"
    / "ESA_WorldCover_10m_2021_v200_N21E072_Map.tif"
)

# Radius around each thermal event used to estimate local land cover.
RADIUS_METERS = 250

# EPSG:4326 raster -> approximate degree conversion.
# At Dahej latitude, this is sufficient for the POC.
METERS_PER_DEGREE_LAT = 111_320
METERS_PER_DEGREE_LON = 103_000


# -------------------------------------------------------------------
# WorldCover classes
# -------------------------------------------------------------------

WORLDCOVER_CLASSES = {
    10: "tree_cover",
    20: "shrubland",
    30: "grassland",
    40: "cropland",
    50: "built_up",
    60: "bare_sparse_vegetation",
    80: "permanent_water",
    90: "herbaceous_wetland",
    95: "mangroves",
    100: "moss_lichen",
}


def dominant_landcover(class_percentages: dict[int, float]) -> str | None:
    """
    Return the dominant WorldCover class.

    Only valid WorldCover pixels are considered.
    """

    if not class_percentages:
        return None

    dominant_code = max(
        class_percentages,
        key=class_percentages.get,
    )

    return WORLDCOVER_CLASSES.get(
        dominant_code,
        f"class_{dominant_code}",
    )


def calculate_landcover(
    dataset,
    latitude: float,
    longitude: float,
) -> dict:

    # Convert 250 m to approximate degrees.
    lat_delta = RADIUS_METERS / METERS_PER_DEGREE_LAT
    lon_delta = RADIUS_METERS / METERS_PER_DEGREE_LON

    left = longitude - lon_delta
    right = longitude + lon_delta
    bottom = latitude - lat_delta
    top = latitude + lat_delta

    window = from_bounds(
        left,
        bottom,
        right,
        top,
        transform=dataset.transform,
    )

    # Read the relevant pixels only.
    data = dataset.read(
        1,
        window=window,
        masked=True,
    )

    values = data.compressed()

    if values.size == 0:
        return {
            "landcover_class": None,
            "forest_fraction": None,
            "cropland_fraction": None,
            "built_up_fraction": None,
        }

    # Remove invalid/no-data pixels.
    values = values[values != 0]

    if values.size == 0:
        return {
            "landcover_class": None,
            "forest_fraction": None,
            "cropland_fraction": None,
            "built_up_fraction": None,
        }

    total = len(values)

    class_percentages = {}

    for class_code in np.unique(values):
        class_code = int(class_code)
        count = int(np.sum(values == class_code))
        class_percentages[class_code] = count / total

    # Vegetation relevant to wildfire evidence.
    vegetation_classes = {
        10,  # tree cover
        20,  # shrubland
        30,  # grassland
        95,  # mangroves
        100,  # moss/lichen
    }

    forest_pixels = np.sum(
        np.isin(values, list(vegetation_classes))
    )

    cropland_pixels = np.sum(values == 40)

    built_up_pixels = np.sum(values == 50)

    return {
        "landcover_class": dominant_landcover(class_percentages),
        "forest_fraction": float(forest_pixels / total),
        "cropland_fraction": float(cropland_pixels / total),
        "built_up_fraction": float(built_up_pixels / total),
    }


def main():

    if not RASTER_PATH.exists():
        raise FileNotFoundError(
            f"WorldCover raster not found:\n{RASTER_PATH}"
        )

    print("WorldCover enrichment started.")
    print(f"Raster: {RASTER_PATH}")
    print(f"Sampling radius: {RADIUS_METERS} m")

    # ---------------------------------------------------------------
    # Open raster
    # ---------------------------------------------------------------

    with rasterio.open(RASTER_PATH) as dataset:

        print(f"CRS: {dataset.crs}")
        print(f"Resolution: {dataset.res}")

        # -----------------------------------------------------------
        # Get Phoenix events
        # -----------------------------------------------------------

        db = SessionLocal()

        try:
            events = db.execute(
                text(
                    """
                    SELECT
                        event_id,
                        latitude,
                        longitude
                    FROM thermal_events
                    ORDER BY event_id
                    """
                )
            ).mappings().all()

            print(f"Events found: {len(events)}")

            updated = 0
            missing = 0

            # -------------------------------------------------------
            # Process events
            # -------------------------------------------------------

            for index, event in enumerate(events, start=1):

                event_id = event["event_id"]
                latitude = event["latitude"]
                longitude = event["longitude"]

                if latitude is None or longitude is None:
                    missing += 1
                    continue

                result = calculate_landcover(
                    dataset,
                    float(latitude),
                    float(longitude),
                )

                db.execute(
                    text(
                        """
                        UPDATE thermal_events
                        SET
                            landcover_class = :landcover_class,
                            forest_fraction = :forest_fraction,
                            cropland_fraction = :cropland_fraction,
                            built_up_fraction = :built_up_fraction,
                            updated_at = NOW()
                        WHERE event_id = :event_id
                        """
                    ),
                    {
                        "event_id": event_id,
                        **result,
                    },
                )

                updated += 1

                if index % 100 == 0:
                    print(
                        f"Processed {index}/{len(events)} events..."
                    )

            db.commit()

            print()
            print("WorldCover enrichment completed.")
            print(f"Events found: {len(events)}")
            print(f"Events updated: {updated}")
            print(f"Events missing coordinates: {missing}")

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


if __name__ == "__main__":
    main()