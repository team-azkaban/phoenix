from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db.database import SessionLocal


# =========================================================
# Paths
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "weather"
    / "processed"
    / "dahej_event_weather_2023.csv"
)


# =========================================================
# Configuration
# =========================================================

# Below this speed, wind direction is treated as
# unreliable for plume/spread interpretation.
CALM_WIND_THRESHOLD = 0.5


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 60)
    print("PHOENIX - LOAD ERA5 2023 WEATHER")
    print("=" * 60)

    # -----------------------------------------------------
    # Check input file
    # -----------------------------------------------------

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            f"\nWeather CSV not found:\n{INPUT_PATH}"
        )

    print("\nInput:")
    print(INPUT_PATH)

    # -----------------------------------------------------
    # Read CSV
    # -----------------------------------------------------

    df = pd.read_csv(INPUT_PATH)

    print(
        f"\nWeather records found: "
        f"{len(df)}"
    )

    required_columns = {
        "event_id",
        "wind_speed",
        "wind_direction",
        "source",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing)}"
        )

    # -----------------------------------------------------
    # Basic validation
    # -----------------------------------------------------

    if df["event_id"].duplicated().any():

        duplicates = (
            df[df["event_id"].duplicated()]
            ["event_id"]
            .tolist()
        )

        raise ValueError(
            "Duplicate event IDs found in "
            f"weather CSV: {duplicates[:10]}"
        )

    invalid_speed = (
        (df["wind_speed"] < 0)
        | (df["wind_speed"].isna())
    )

    if invalid_speed.any():

        raise ValueError(
            "Invalid wind speed values found."
        )

    # -----------------------------------------------------
    # Apply calm-wind rule
    # -----------------------------------------------------

    calm_mask = (
        df["wind_speed"]
        < CALM_WIND_THRESHOLD
    )

    calm_count = int(
        calm_mask.sum()
    )

    df.loc[
        calm_mask,
        "wind_direction"
    ] = None

    print(
        f"\nCalm/near-calm events "
        f"(< {CALM_WIND_THRESHOLD} m/s): "
        f"{calm_count}"
    )

    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Verify all event IDs exist
        # -------------------------------------------------

        event_ids = [
            str(event_id)
            for event_id in df["event_id"]
        ]

        existing_rows = db.execute(
            text(
                """
                SELECT event_id
                FROM thermal_events
                WHERE event_id = ANY(
                    CAST(:event_ids AS uuid[])
                )
                """
            ),
            {
                "event_ids":
                    "{" + ",".join(event_ids) + "}"
            }
        ).fetchall()

        existing_ids = {
            str(row[0])
            for row in existing_rows
        }

        missing_ids = (
            set(event_ids)
            - existing_ids
        )

        print(
            f"\nEvents found in database: "
            f"{len(existing_ids)}"
        )

        print(
            f"Events missing from database: "
            f"{len(missing_ids)}"
        )

        if missing_ids:

            print(
                "\nFirst missing IDs:"
            )

            for event_id in list(
                missing_ids
            )[:10]:

                print(
                    f"  {event_id}"
                )

            raise ValueError(
                "Stopping because some weather "
                "records do not have matching "
                "thermal events."
            )

        # -------------------------------------------------
        # Update thermal events
        # -------------------------------------------------

        update_sql = text(
            """
            UPDATE thermal_events
            SET
                wind_speed = :wind_speed,
                wind_direction = :wind_direction,
                updated_at = NOW()
            WHERE event_id = CAST(
                :event_id AS uuid
            )
            """
        )

        updated = 0

        for _, row in df.iterrows():

            wind_direction = row[
                "wind_direction"
            ]

            if pd.isna(
                wind_direction
            ):
                wind_direction = None
            else:
                wind_direction = float(
                    wind_direction
                )

            db.execute(
                update_sql,
                {
                    "event_id":
                        str(row["event_id"]),

                    "wind_speed":
                        float(
                            row["wind_speed"]
                        ),

                    "wind_direction":
                        wind_direction,
                }
            )

            updated += 1

            if updated % 250 == 0:

                print(
                    f"Updated {updated} "
                    f"/ {len(df)} events..."
                )

        db.commit()

        print(
            f"\nSuccessfully updated: "
            f"{updated} events"
        )

        # =================================================
        # Verification
        # =================================================

        verification = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_2023,
                    COUNT(wind_speed) AS with_wind_speed,
                    COUNT(wind_direction) AS with_direction,
                    MIN(wind_speed) AS min_speed,
                    MAX(wind_speed) AS max_speed,
                    AVG(wind_speed) AS mean_speed
                FROM thermal_events
                WHERE first_seen >=
                    '2023-01-01 00:00:00+00'
                  AND first_seen <
                    '2024-01-01 00:00:00+00'
                """
            )
        ).mappings().one()

        print("\n" + "=" * 60)
        print("SUPABASE VERIFICATION")
        print("=" * 60)

        print(
            f"\n2023 thermal events: "
            f"{verification['total_2023']}"
        )

        print(
            f"With wind speed: "
            f"{verification['with_wind_speed']}"
        )

        print(
            f"With wind direction: "
            f"{verification['with_direction']}"
        )

        print(
            f"Minimum wind speed: "
            f"{verification['min_speed']:.2f} m/s"
        )

        print(
            f"Maximum wind speed: "
            f"{verification['max_speed']:.2f} m/s"
        )

        print(
            f"Mean wind speed: "
            f"{verification['mean_speed']:.2f} m/s"
        )

        # -------------------------------------------------
        # Check for missing weather
        # -------------------------------------------------

        missing_weather = db.execute(
            text(
                """
                SELECT COUNT(*) AS count
                FROM thermal_events
                WHERE first_seen >=
                    '2023-01-01 00:00:00+00'
                  AND first_seen <
                    '2024-01-01 00:00:00+00'
                  AND wind_speed IS NULL
                """
            )
        ).scalar_one()

        print(
            f"\n2023 events without wind speed: "
            f"{missing_weather}"
        )

        if missing_weather == 0:

            print(
                "\n✓ All 2023 events have "
                "wind speed."
            )

        else:

            print(
                "\n⚠ Some 2023 events are "
                "missing wind speed."
            )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()

    print("\nDone.")


if __name__ == "__main__":
    main()