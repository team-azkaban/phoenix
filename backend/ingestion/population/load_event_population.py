from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import func

# -------------------------------------------------------------------
# Project paths
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "population"
    / "processed"
    / "dahej_event_population_2024.csv"
)

# -------------------------------------------------------------------
# Validation settings
# -------------------------------------------------------------------

EXPECTED_EVENT_COUNT = 2806


def main():
    print("=" * 70)
    print("PHOENIX - LOAD EVENT POPULATION EXPOSURE")
    print("=" * 70)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Population CSV not found:\n{INPUT_CSV}"
        )

    # Make backend imports available.
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

    from db.database import SessionLocal
    from db.models.thermal_event import ThermalEvent

    # ----------------------------------------------------------------
    # Read CSV
    # ----------------------------------------------------------------

    print(f"\nInput CSV:")
    print(INPUT_CSV)

    df = pd.read_csv(INPUT_CSV)

    required_columns = {
        "event_id",
        "event_timestamp",
        "event_latitude",
        "event_longitude",
        "exposure_radius_m",
        "population_exposed",
        "population_pixels",
        "source",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    print(f"\nCSV records: {len(df)}")

    # ----------------------------------------------------------------
    # Validate CSV
    # ----------------------------------------------------------------

    if len(df) != EXPECTED_EVENT_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_EVENT_COUNT} CSV records, "
            f"found {len(df)}."
        )

    if df["event_id"].duplicated().any():
        duplicates = (
            df.loc[
                df["event_id"].duplicated(keep=False),
                "event_id",
            ]
            .tolist()
        )

        raise ValueError(
            f"Duplicate event IDs found: {duplicates[:10]}"
        )

    if df["population_exposed"].isna().any():
        raise ValueError(
            "Population exposure contains NULL/NaN values."
        )

    if (df["population_exposed"] < 0).any():
        raise ValueError(
            "Negative population exposure detected."
        )

    if (df["population_pixels"] < 0).any():
        raise ValueError(
            "Negative population pixel count detected."
        )

    radius_values = df["exposure_radius_m"].dropna().unique()

    if len(radius_values) != 1 or float(radius_values[0]) != 250.0:
        raise ValueError(
            f"Unexpected exposure radius values: {radius_values}"
        )

    print("✓ CSV structure valid")
    print("✓ No duplicate event IDs")
    print("✓ No missing population values")
    print("✓ No negative population values")
    print("✓ Exposure radius = 250 m")

    # ----------------------------------------------------------------
    # Connect to database
    # ----------------------------------------------------------------

    db = SessionLocal()

    try:
        event_ids = df["event_id"].astype(str).tolist()

        # ------------------------------------------------------------
        # Verify all CSV event IDs exist in Supabase
        # ------------------------------------------------------------

        database_events = (
            db.query(ThermalEvent.event_id)
            .filter(ThermalEvent.event_id.in_(event_ids))
            .all()
        )

        database_event_ids = {
            str(row[0])
            for row in database_events
        }

        missing_ids = (
            set(event_ids)
            - database_event_ids
        )

        if missing_ids:
            raise ValueError(
                f"{len(missing_ids)} CSV events are missing "
                f"from Supabase. Examples: "
                f"{list(missing_ids)[:10]}"
            )

        print(
            f"\nDatabase events found: "
            f"{len(database_event_ids)}"
        )

        print("✓ All CSV event IDs exist in Supabase")

        # ------------------------------------------------------------
        # Update population_exposed
        # ------------------------------------------------------------

        print("\nUpdating thermal_events.population_exposed...")

        updated = 0

        for row in df.itertuples(index=False):

            event = (
                db.query(ThermalEvent)
                .filter(
                    ThermalEvent.event_id
                    == row.event_id
                )
                .one_or_none()
            )

            if event is None:
                raise ValueError(
                    f"Event disappeared during update: "
                    f"{row.event_id}"
                )

            event.population_exposed = float(
                row.population_exposed
            )

            updated += 1

            if updated % 250 == 0:
                print(
                    f"  Updated "
                    f"{updated}/{len(df)} events"
                )

        # Commit only after every row has been validated/updated.
        db.commit()

        print(
            f"\n✓ Successfully updated: "
            f"{updated} events"
        )

        # ----------------------------------------------------------------
        # Verify database values
        # ----------------------------------------------------------------

        print("\nVerifying Supabase values...")

        db_values = (
            db.query(
                ThermalEvent.event_id,
                ThermalEvent.population_exposed,
            )
            .filter(
                ThermalEvent.event_id.in_(event_ids)
            )
            .all()
        )

        db_map = {
            str(event_id): population
            for event_id, population in db_values
        }

        if len(db_map) != len(df):
            raise ValueError(
                "Database verification count does not "
                "match CSV count."
            )

        mismatches = []

        for row in df.itertuples(index=False):

            csv_value = float(
                row.population_exposed
            )

            db_value = db_map.get(
                str(row.event_id)
            )

            if db_value is None:
                mismatches.append(
                    (
                        row.event_id,
                        csv_value,
                        None,
                    )
                )
                continue

            # Floating-point comparison.
            if abs(
                float(db_value) - csv_value
            ) > 1e-6:

                mismatches.append(
                    (
                        row.event_id,
                        csv_value,
                        float(db_value),
                    )
                )

        if mismatches:
            raise ValueError(
                f"Found {len(mismatches)} population "
                f"value mismatches. Examples: "
                f"{mismatches[:5]}"
            )

        print("✓ CSV and Supabase values match")

        # ----------------------------------------------------------------
        # Final statistics from Supabase
        # ----------------------------------------------------------------

        stats = (
            db.query(
                func.min(
                    ThermalEvent.population_exposed
                ),
                func.max(
                    ThermalEvent.population_exposed
                ),
                func.avg(
                    ThermalEvent.population_exposed
                ),
            )
            .filter(
                ThermalEvent.event_id.in_(event_ids)
            )
            .one()
        )

        min_population = float(
            stats[0]
        )
        max_population = float(
            stats[1]
        )
        mean_population = float(
            stats[2]
        )

        nonzero_count = (
            db.query(ThermalEvent)
            .filter(
                ThermalEvent.event_id.in_(event_ids),
                ThermalEvent.population_exposed > 0,
            )
            .count()
        )

        zero_count = (
            db.query(ThermalEvent)
            .filter(
                ThermalEvent.event_id.in_(event_ids),
                ThermalEvent.population_exposed == 0,
            )
            .count()
        )

        print("\n" + "=" * 70)
        print("POPULATION LOAD COMPLETE")
        print("=" * 70)

        print("\nSupabase verification:")
        print(f"  Events updated: {updated}")
        print(
            f"  Events with population > 0: "
            f"{nonzero_count}"
        )
        print(
            f"  Events with population = 0: "
            f"{zero_count}"
        )
        print(
            f"  Minimum population: "
            f"{min_population:.2f}"
        )
        print(
            f"  Mean population: "
            f"{mean_population:.2f}"
        )
        print(
            f"  Maximum population: "
            f"{max_population:.2f}"
        )

        print("\n✓ population_exposed successfully loaded.")
        print("✓ Database verification passed.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()