from pathlib import Path
import sys

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from db.database import SessionLocal


CLASSES = [
    "agricultural_burn",
    "wildfire",
    "gas_flare",
    "industrial_fire",
    "mixed_or_uncertain",
]


def main():
    db = SessionLocal()

    try:
        for classification in CLASSES:

            print("\n" + "=" * 80)
            print(f"CLASS: {classification}")
            print("=" * 80)

            rows = db.execute(
                text(
                    """
                    SELECT
                        event_id,
                        first_seen,
                        latitude,
                        longitude,
                        current_frp,
                        max_frp,
                        observation_count,
                        duration,
                        facility_type,
                        facility_distance_m,
                        landcover_class,
                        cropland_fraction,
                        forest_fraction,
                        built_up_fraction,
                        classification_confidence,
                        classification_reasons
                    FROM thermal_events
                    WHERE classification = :classification
                    ORDER BY max_frp DESC NULLS LAST
                    LIMIT 5
                    """
                ),
                {
                    "classification": classification
                },
            ).mappings().all()

            if not rows:
                print("No events found.")
                continue

            for i, row in enumerate(rows, start=1):

                print(f"\n--- Event {i} ---")
                print(f"event_id:              {row['event_id']}")
                print(f"timestamp:             {row['first_seen']}")
                print(
                    f"location:              "
                    f"{row['latitude']}, {row['longitude']}"
                )
                print(f"current_frp:           {row['current_frp']}")
                print(f"max_frp:               {row['max_frp']}")
                print(
                    f"observation_count:     "
                    f"{row['observation_count']}"
                )
                print(f"duration:              {row['duration']}")
                print(f"facility_type:         {row['facility_type']}")
                print(
                    f"facility_distance_m:   "
                    f"{row['facility_distance_m']}"
                )
                print(
                    f"landcover_class:       "
                    f"{row['landcover_class']}"
                )
                print(
                    f"cropland_fraction:     "
                    f"{row['cropland_fraction']}"
                )
                print(
                    f"forest_fraction:       "
                    f"{row['forest_fraction']}"
                )
                print(
                    f"built_up_fraction:     "
                    f"{row['built_up_fraction']}"
                )
                print(
                    f"confidence:            "
                    f"{row['classification_confidence']}"
                )
                print(
                    "reasons:"
                )
                print(row["classification_reasons"])

    finally:
        db.close()


if __name__ == "__main__":
    main()