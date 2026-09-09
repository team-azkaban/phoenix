"""
Enrich existing PHOENIX Dahej thermal events with:

1. Nearest/associated facility context
2. Facility distance
3. Facility type
4. Event FRP statistics
5. Event duration

Sources:
    data/firms/dahej/dahej_candidate_events.csv
    data/firms/dahej/dahej_event_observations.csv
    data/firms/dahej/dahej_firms_observations.csv
    data/firms/dahej/dahej_event_industrial_context.csv
    data/facilities/dahej/dahej_facilities.csv

Target:
    Supabase/PostgreSQL thermal_events

IMPORTANT:
    - Does NOT create new thermal events.
    - Does NOT modify classification.
    - Does NOT populate baseline/anomaly/satellite/risk/alerts/emissions.
    - Uses the same deterministic UUID mapping as the Supabase loader.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Project path
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

from db.database import SessionLocal


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"

EVENTS_FILE = (
    DATA_DIR
    / "firms"
    / "dahej"
    / "dahej_candidate_events.csv"
)

EVENT_OBSERVATIONS_FILE = (
    DATA_DIR
    / "firms"
    / "dahej"
    / "dahej_event_observations.csv"
)

OBSERVATIONS_FILE = (
    DATA_DIR
    / "firms"
    / "dahej"
    / "dahej_firms_observations.csv"
)

FACILITY_CONTEXT_FILE = (
    DATA_DIR
    / "firms"
    / "dahej"
    / "dahej_event_industrial_context.csv"
)

FACILITIES_FILE = (
    DATA_DIR
    / "facilities"
    / "dahej"
    / "dahej_facilities.csv"
)


# ---------------------------------------------------------------------------
# UUID mapping
# ---------------------------------------------------------------------------

def stable_uuid(identifier: str) -> str:
    """
    Convert PHOENIX human-readable IDs into deterministic UUIDs.

    This MUST match the UUID mapping used by load_dahej_poc.py.
    """
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"phoenix-dahej:{identifier}",
        )
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def to_float(value):
    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Load source data
# ---------------------------------------------------------------------------

def load_data():
    print("\nLoading source files...")

    for path in [
        EVENTS_FILE,
        EVENT_OBSERVATIONS_FILE,
        OBSERVATIONS_FILE,
        FACILITY_CONTEXT_FILE,
        FACILITIES_FILE,
    ]:
        require_file(path)

    events = pd.read_csv(EVENTS_FILE)
    event_observations = pd.read_csv(EVENT_OBSERVATIONS_FILE)
    observations = pd.read_csv(OBSERVATIONS_FILE)
    facility_context = pd.read_csv(FACILITY_CONTEXT_FILE)
    facilities = pd.read_csv(FACILITIES_FILE)

    print(f"  Events:             {len(events):,}")
    print(f"  Event mappings:     {len(event_observations):,}")
    print(f"  Observations:       {len(observations):,}")
    print(f"  Facility context:   {len(facility_context):,}")
    print(f"  Facilities:         {len(facilities):,}")

    return (
        events,
        event_observations,
        observations,
        facility_context,
        facilities,
    )


# ---------------------------------------------------------------------------
# Normalize observation timestamps / FRP
# ---------------------------------------------------------------------------

def prepare_observations(observations: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the FIRMS observations used to calculate event statistics.
    """

    if "observation_id" not in observations.columns:
        raise ValueError(
            "dahej_firms_observations.csv is missing observation_id"
        )

    if "frp" not in observations.columns:
        raise ValueError(
            "dahej_firms_observations.csv is missing frp"
        )

    timestamp_column = first_existing_column(
        observations,
        [
            "timestamp",
            "acquisition_timestamp",
            "acq_datetime",
        ],
    )

    if timestamp_column is None:
        raise ValueError(
            "Could not find an observation timestamp column."
        )

    observations = observations.copy()

    observations["_timestamp"] = pd.to_datetime(
        observations[timestamp_column],
        errors="coerce",
        utc=True,
    )

    observations["_frp"] = pd.to_numeric(
        observations["frp"],
        errors="coerce",
    )

    invalid_timestamp = observations["_timestamp"].isna().sum()

    if invalid_timestamp:
        print(
            f"  Warning: removing {invalid_timestamp:,} "
            "observations with invalid timestamps."
        )

    observations = observations[
        observations["_timestamp"].notna()
    ].copy()

    return observations


# ---------------------------------------------------------------------------
# Calculate event statistics
# ---------------------------------------------------------------------------

def calculate_event_statistics(
    events: pd.DataFrame,
    event_observations: pd.DataFrame,
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate:

        current_frp
        max_frp
        mean_frp
        duration

    from the actual observation records.
    """

    required_event_mapping_columns = {
        "event_id",
        "observation_id",
    }

    missing = (
        required_event_mapping_columns
        - set(event_observations.columns)
    )

    if missing:
        raise ValueError(
            "Event mapping file missing columns: "
            + ", ".join(sorted(missing))
        )

    print("\nCalculating event statistics...")

    merged = event_observations[
        ["event_id", "observation_id"]
    ].merge(
        observations[
            [
                "observation_id",
                "_timestamp",
                "_frp",
            ]
        ],
        on="observation_id",
        how="left",
        validate="many_to_one",
    )

    # Check for orphan observation references.
    missing_observations = merged["_timestamp"].isna().sum()

    if missing_observations:
        raise ValueError(
            f"{missing_observations:,} event-observation mappings "
            "could not be matched to an observation."
        )

    grouped = (
        merged
        .sort_values(
            ["event_id", "_timestamp"],
        )
        .groupby("event_id", as_index=False)
        .agg(
            first_seen_calculated=(
                "_timestamp",
                "min",
            ),
            last_seen_calculated=(
                "_timestamp",
                "max",
            ),
            max_frp_calculated=(
                "_frp",
                "max",
            ),
            mean_frp_calculated=(
                "_frp",
                "mean",
            ),
        )
    )

    # Current FRP = FRP from latest observation.
    latest = (
        merged
        .sort_values(
            ["event_id", "_timestamp"],
        )
        .groupby("event_id", as_index=False)
        .tail(1)
        [
            [
                "event_id",
                "_frp",
            ]
        ]
        .rename(
            columns={
                "_frp": "current_frp_calculated",
            }
        )
    )

    stats = grouped.merge(
        latest,
        on="event_id",
        how="left",
        validate="one_to_one",
    )

    stats["duration_calculated"] = (
        stats["last_seen_calculated"]
        - stats["first_seen_calculated"]
    ).dt.total_seconds() / 3600.0

    print(
        f"  Events with calculated statistics: "
        f"{len(stats):,}"
    )

    return stats


# ---------------------------------------------------------------------------
# Prepare facility enrichment
# ---------------------------------------------------------------------------

def prepare_facility_context(
    facility_context: pd.DataFrame,
    facilities: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare nearest-facility relationships.

    Expected context columns:

        event_id
        nearest_facility_id
        nearest_facility_type
        facility_distance_m

    The facility CSV is used to validate that referenced facilities exist.
    """

    print("\nPreparing facility enrichment...")

    required_context = {
        "event_id",
        "nearest_facility_id",
        "facility_distance_m",
    }

    missing = required_context - set(facility_context.columns)

    if missing:
        raise ValueError(
            "Facility context file missing columns: "
            + ", ".join(sorted(missing))
        )

    if "facility_id" not in facilities.columns:
        raise ValueError(
            "Facility file is missing facility_id"
        )

    facility_context = facility_context.copy()
    facilities = facilities.copy()

    known_facilities = set(
        facilities["facility_id"]
        .dropna()
        .astype(str)
    )

    facility_context["nearest_facility_id"] = (
        facility_context["nearest_facility_id"]
        .astype("string")
    )

    # Validate facility references.
    referenced = set(
        facility_context["nearest_facility_id"]
        .dropna()
        .astype(str)
    )

    unknown_facilities = referenced - known_facilities

    if unknown_facilities:
        raise ValueError(
            "Facility context references unknown facilities: "
            + ", ".join(sorted(unknown_facilities))
        )

    # Normalize numeric distance.
    facility_context["facility_distance_m"] = pd.to_numeric(
        facility_context["facility_distance_m"],
        errors="coerce",
    )

    # Find facility type.
    context_type_column = first_existing_column(
        facility_context,
        [
            "nearest_facility_type",
            "facility_type",
        ],
    )

    if context_type_column is None:
        context_type_column = None

    output_columns = [
        "event_id",
        "nearest_facility_id",
        "facility_distance_m",
    ]

    if context_type_column:
        output_columns.append(context_type_column)

    context = facility_context[output_columns].copy()

    rename_map = {
        "nearest_facility_id": "facility_id",
    }

    if context_type_column:
        rename_map[context_type_column] = "facility_type"

    context = context.rename(columns=rename_map)

    # There should be one enrichment record per event.
    duplicate_events = (
        context["event_id"]
        .duplicated(keep=False)
    )

    if duplicate_events.any():
        duplicates = (
            context.loc[
                duplicate_events,
                "event_id",
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            "Facility context contains multiple records "
            f"for {len(duplicates)} events."
        )

    # Convert human-readable facility ID to same UUID used by loader.
    context["facility_uuid"] = context["facility_id"].apply(
        lambda value: (
            stable_uuid(str(value))
            if pd.notna(value)
            else None
        )
    )

    print(
        f"  Facility-enriched events: "
        f"{context['facility_uuid'].notna().sum():,}"
    )

    return context


# ---------------------------------------------------------------------------
# Update database
# ---------------------------------------------------------------------------

def update_database(
    events: pd.DataFrame,
    stats: pd.DataFrame,
    facility_context: pd.DataFrame,
) -> None:
    """
    Update existing thermal_events records.
    """

    print("\nUpdating Supabase thermal_events...")

    stats_by_event = {
        str(row["event_id"]): row
        for _, row in stats.iterrows()
    }

    facilities_by_event = {
        str(row["event_id"]): row
        for _, row in facility_context.iterrows()
    }

    event_ids = (
        events["event_id"]
        .dropna()
        .astype(str)
        .tolist()
    )

    print(
        f"  Events to process: {len(event_ids):,}"
    )

    db = SessionLocal()

    updated = 0
    missing_stats = 0
    missing_facility = 0

    try:
        # Verify database event count first.
        db_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events
                """
            )
        ).scalar_one()

        print(
            f"  thermal_events currently contains: "
            f"{db_count:,} rows"
        )

        if db_count != len(event_ids):
            raise RuntimeError(
                "Database event count does not match local "
                "candidate event count. Refusing to update."
            )

        # Make sure every local event exists in DB.
        db_event_rows = db.execute(
            text(
                """
                SELECT event_id
                FROM thermal_events
                """
            )
        ).fetchall()

        db_event_ids = {
            str(row[0])
            for row in db_event_rows
        }

        # Local event IDs are human-readable, while DB IDs are UUIDs.
        expected_db_ids = {
            stable_uuid(event_id)
            for event_id in event_ids
        }

        missing_db_ids = expected_db_ids - db_event_ids

        if missing_db_ids:
            raise RuntimeError(
                f"{len(missing_db_ids):,} local events are "
                "missing from thermal_events."
            )

        # Update one event at a time.
        update_sql = text(
            """
            UPDATE thermal_events
            SET
                facility_id = :facility_id,
                facility_distance_m = :facility_distance_m,
                facility_type = :facility_type,
                current_frp = :current_frp,
                max_frp = :max_frp,
                mean_frp = :mean_frp,
                duration = :duration,
                updated_at = now()
            WHERE event_id = :event_id
            """
        )

        for event_id in event_ids:
            db_event_id = stable_uuid(event_id)

            stat = stats_by_event.get(event_id)

            if stat is None:
                missing_stats += 1
                continue

            facility = facilities_by_event.get(event_id)

            if facility is None:
                missing_facility += 1

            facility_uuid = None
            facility_distance = None
            facility_type = None

            if facility is not None:
                facility_uuid = facility.get(
                    "facility_uuid"
                )

                facility_distance = to_float(
                    facility.get("facility_distance_m")
                )

                if "facility_type" in facility.index:
                    facility_type = facility.get(
                        "facility_type"
                    )

                    if pd.isna(facility_type):
                        facility_type = None

            params = {
                "event_id": db_event_id,

                "facility_id": facility_uuid,
                "facility_distance_m": facility_distance,
                "facility_type": facility_type,

                "current_frp": to_float(
                    stat.get(
                        "current_frp_calculated"
                    )
                ),

                "max_frp": to_float(
                    stat.get(
                        "max_frp_calculated"
                    )
                ),

                "mean_frp": to_float(
                    stat.get(
                        "mean_frp_calculated"
                    )
                ),

                "duration": to_float(
                    stat.get(
                        "duration_calculated"
                    )
                ),
            }

            result = db.execute(
                update_sql,
                params,
            )

            if result.rowcount != 1:
                raise RuntimeError(
                    f"Expected to update one event, "
                    f"but updated {result.rowcount}: "
                    f"{event_id}"
                )

            updated += 1

            # Commit periodically.
            if updated % 250 == 0:
                db.commit()
                print(
                    f"  Updated {updated:,}/{len(event_ids):,}"
                )

        db.commit()

        print(
            f"\n  Successfully updated: {updated:,}"
        )

        print(
            f"  Missing event statistics: "
            f"{missing_stats:,}"
        )

        print(
            f"  Events without facility context: "
            f"{missing_facility:,}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_database() -> None:
    """
    Validate the resulting thermal_events table.
    """

    print("\nRunning database validation...")

    db = SessionLocal()

    try:
        row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_events,

                    COUNT(facility_id)
                        AS events_with_facility,

                    COUNT(facility_distance_m)
                        AS events_with_distance,

                    COUNT(facility_type)
                        AS events_with_facility_type,

                    COUNT(current_frp)
                        AS events_with_current_frp,

                    COUNT(max_frp)
                        AS events_with_max_frp,

                    COUNT(mean_frp)
                        AS events_with_mean_frp,

                    COUNT(duration)
                        AS events_with_duration,

                    COUNT(classification)
                        AS classified_events,

                    COUNT(baseline_frp)
                        AS baseline_events

                FROM thermal_events
                """
            )
        ).mappings().one()

        print("\nThermal event database status:")
        print(
            f"  Total events:             "
            f"{row['total_events']:,}"
        )
        print(
            f"  With facility:            "
            f"{row['events_with_facility']:,}"
        )
        print(
            f"  With facility distance:   "
            f"{row['events_with_distance']:,}"
        )
        print(
            f"  With facility type:       "
            f"{row['events_with_facility_type']:,}"
        )
        print(
            f"  With current FRP:         "
            f"{row['events_with_current_frp']:,}"
        )
        print(
            f"  With max FRP:             "
            f"{row['events_with_max_frp']:,}"
        )
        print(
            f"  With mean FRP:            "
            f"{row['events_with_mean_frp']:,}"
        )
        print(
            f"  With duration:            "
            f"{row['events_with_duration']:,}"
        )
        print(
            f"  Classified:               "
            f"{row['classified_events']:,}"
        )
        print(
            f"  With baseline:            "
            f"{row['baseline_events']:,}"
        )

        # Facility distance distribution.
        distance_rows = db.execute(
            text(
                """
                SELECT
                    CASE
                        WHEN facility_distance_m < 500
                            THEN '<500m'
                        WHEN facility_distance_m < 1000
                            THEN '500m-1km'
                        WHEN facility_distance_m < 2000
                            THEN '1-2km'
                        WHEN facility_distance_m < 5000
                            THEN '2-5km'
                        ELSE '>5km'
                    END AS distance_band,
                    COUNT(*) AS event_count
                FROM thermal_events
                WHERE facility_distance_m IS NOT NULL
                GROUP BY 1
                ORDER BY
                    CASE
                        WHEN facility_distance_m < 500
                            THEN 1
                        WHEN facility_distance_m < 1000
                            THEN 2
                        WHEN facility_distance_m < 2000
                            THEN 3
                        WHEN facility_distance_m < 5000
                            THEN 4
                        ELSE 5
                    END
                """
            )
        ).mappings().all()

        print("\nFacility distance bands:")

        for distance_row in distance_rows:
            print(
                f"  {distance_row['distance_band']:12s} "
                f"{distance_row['event_count']:,}"
            )

        # Check invalid facility references.
        orphan_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events te
                LEFT JOIN facilities f
                    ON f.facility_id = te.facility_id
                WHERE
                    te.facility_id IS NOT NULL
                    AND f.facility_id IS NULL
                """
            )
        ).scalar_one()

        print(
            f"\nOrphan facility references: "
            f"{orphan_count:,}"
        )

        if orphan_count != 0:
            raise RuntimeError(
                "Validation failed: orphan facility references found."
            )

        print("\nDatabase validation passed.")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("PHOENIX — Dahej Thermal Event Enrichment")
    print("=" * 70)

    (
        events,
        event_observations,
        observations,
        facility_context,
        facilities,
    ) = load_data()

    # Normalize observations.
    observations = prepare_observations(
        observations
    )

    # Calculate event-level FRP/duration statistics.
    stats = calculate_event_statistics(
        events,
        event_observations,
        observations,
    )

    # Prepare facility relationships.
    facility_context = prepare_facility_context(
        facility_context,
        facilities,
    )

    # Safety check: local event count.
    if len(events) != 2806:
        print(
            "\nWARNING:"
            f" local event count is {len(events):,}, "
            "not the expected 2,806."
        )

    # Update existing database records.
    update_database(
        events,
        stats,
        facility_context,
    )

    # Validate.
    validate_database()

    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)

    print(
        """
Next stage:
    Rule-based thermal event classification.

Not populated by this script:
    - baseline_frp
    - baseline_deviation
    - anomaly_state
    - classification
    - classification_confidence
    - classification_reasons
    - satellite fields
    - emissions
    - population exposure
    - wind
    - risk
    - alerts
"""
    )


if __name__ == "__main__":
    main()