"""
Build and load PHOENIX site baselines.

Source:
    thermal_events

Target:
    site_baselines

One baseline is created for every facility that has at least one
facility-linked thermal event.

Baseline fields:
    baseline_frp
    frp_std
    typical_active_hours
    typical_duration
    seasonal_pattern
    historical_event_count

The calculation uses the historical thermal_events already stored
in Supabase.

Run from project root:

    $env:PYTHONPATH="backend"
    python backend\ingestion\baselines\build_site_baselines.py
"""

from __future__ import annotations

import json
import statistics
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import text

from db.database import SessionLocal


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

UUID_NAMESPACE = uuid.NAMESPACE_URL


def stable_baseline_uuid(facility_id: str) -> str:
    """
    Deterministic UUID so the loader is safely rerunnable.
    """
    return str(
        uuid.uuid5(
            UUID_NAMESPACE,
            f"phoenix-dahej-baseline:{facility_id}",
        )
    )


# ---------------------------------------------------------------------
# Fetch events
# ---------------------------------------------------------------------

def fetch_facility_events(db) -> list[dict[str, Any]]:
    """
    Fetch historical thermal events that are linked to facilities.
    """

    result = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                facility_id::text AS facility_id,
                first_seen,
                last_seen,
                current_frp,
                mean_frp,
                max_frp,
                duration
            FROM thermal_events
            WHERE facility_id IS NOT NULL
              AND current_frp IS NOT NULL
            ORDER BY facility_id, first_seen
            """
        )
    )

    rows = []

    for row in result:

        rows.append(
            {
                "event_id": str(row.event_id),
                "facility_id": str(row.facility_id),
                "first_seen": row.first_seen,
                "last_seen": row.last_seen,
                "current_frp": (
                    float(row.current_frp)
                    if row.current_frp is not None
                    else None
                ),
                "mean_frp": (
                    float(row.mean_frp)
                    if row.mean_frp is not None
                    else None
                ),
                "max_frp": (
                    float(row.max_frp)
                    if row.max_frp is not None
                    else None
                ),
                "duration": (
                    float(row.duration)
                    if row.duration is not None
                    else 0.0
                ),
            }
        )

    return rows


# ---------------------------------------------------------------------
# Calculate baseline
# ---------------------------------------------------------------------

def calculate_baseline(
    facility_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate one baseline for a facility.
    """

    frps = [
        event["current_frp"]
        for event in facility_events
        if event["current_frp"] is not None
    ]

    durations = [
        event["duration"]
        for event in facility_events
        if event["duration"] is not None
        and event["duration"] >= 0
    ]

    # -------------------------------------------------------------
    # FRP baseline
    # -------------------------------------------------------------

    if frps:

        baseline_frp = statistics.mean(frps)

        if len(frps) > 1:
            frp_std = statistics.stdev(frps)
        else:
            frp_std = 0.0

    else:

        baseline_frp = 0.0
        frp_std = 0.0

    # -------------------------------------------------------------
    # Typical duration
    # -------------------------------------------------------------

    if durations:
        typical_duration = statistics.median(
            durations
        )
    else:
        typical_duration = 0.0

    # -------------------------------------------------------------
    # Typical active hours
    #
    # Count the UTC hour in which historical events
    # started.
    # -------------------------------------------------------------

    hour_counter = Counter()

    for event in facility_events:

        timestamp = event["first_seen"]

        if timestamp is None:
            continue

        if hasattr(timestamp, "hour"):
            hour_counter[timestamp.hour] += 1

    if hour_counter:

        total = sum(hour_counter.values())

        typical_active_hours = {
            str(hour): round(
                count / total,
                4,
            )
            for hour, count in sorted(
                hour_counter.items()
            )
        }

    else:

        typical_active_hours = {}

    # -------------------------------------------------------------
    # Seasonal pattern
    #
    # Month -> fraction of facility events.
    # -------------------------------------------------------------

    month_counter = Counter()

    for event in facility_events:

        timestamp = event["first_seen"]

        if timestamp is None:
            continue

        if hasattr(timestamp, "month"):
            month_counter[timestamp.month] += 1

    if month_counter:

        total = sum(month_counter.values())

        seasonal_pattern = {
            str(month): round(
                count / total,
                4,
            )
            for month, count in sorted(
                month_counter.items()
            )
        }

    else:

        seasonal_pattern = {}

    return {
        "baseline_frp": round(
            baseline_frp,
            6,
        ),
        "frp_std": round(
            frp_std,
            6,
        ),
        "typical_active_hours": (
            typical_active_hours
        ),
        "typical_duration": round(
            typical_duration,
            6,
        ),
        "seasonal_pattern": seasonal_pattern,
        "historical_event_count": len(
            facility_events
        ),
    }


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------

def load_baselines() -> None:

    print("=" * 70)
    print("PHOENIX — BUILD SITE BASELINES")
    print("=" * 70)

    db = SessionLocal()

    try:

        # ---------------------------------------------------------
        # Fetch events
        # ---------------------------------------------------------

        events = fetch_facility_events(db)

        print(
            f"\nFacility-linked events: "
            f"{len(events):,}"
        )

        if not events:
            raise RuntimeError(
                "No facility-linked thermal events found."
            )

        # ---------------------------------------------------------
        # Group events by facility
        # ---------------------------------------------------------

        grouped: dict[
            str,
            list[dict[str, Any]]
        ] = defaultdict(list)

        for event in events:

            grouped[
                event["facility_id"]
            ].append(event)

        print(
            f"Facilities with historical events: "
            f"{len(grouped):,}"
        )

        # ---------------------------------------------------------
        # Load baselines
        # ---------------------------------------------------------

        inserted = 0
        updated = 0

        total_events = 0

        for facility_id, facility_events in sorted(
            grouped.items()
        ):

            baseline = calculate_baseline(
                facility_events
            )

            total_events += (
                baseline["historical_event_count"]
            )

            baseline_id = stable_baseline_uuid(
                facility_id
            )

            # -----------------------------------------------------
            # Upsert
            # -----------------------------------------------------

            existing = db.execute(
                text(
                    """
                    SELECT baseline_id
                    FROM site_baselines
                    WHERE facility_id = :facility_id
                    """
                ),
                {
                    "facility_id": facility_id,
                },
            ).scalar_one_or_none()

            if existing is None:

                db.execute(
                    text(
                        """
                        INSERT INTO site_baselines (
                            baseline_id,
                            facility_id,
                            baseline_frp,
                            frp_std,
                            typical_active_hours,
                            typical_duration,
                            seasonal_pattern,
                            historical_event_count,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :baseline_id,
                            :facility_id,
                            :baseline_frp,
                            :frp_std,
                            CAST(
                                :typical_active_hours
                                AS jsonb
                            ),
                            :typical_duration,
                            CAST(
                                :seasonal_pattern
                                AS jsonb
                            ),
                            :historical_event_count,
                            NOW(),
                            NOW()
                        )
                        """
                    ),
                    {
                        "baseline_id": baseline_id,
                        "facility_id": facility_id,
                        "baseline_frp": baseline[
                            "baseline_frp"
                        ],
                        "frp_std": baseline[
                            "frp_std"
                        ],
                        "typical_active_hours": json.dumps(
                            baseline[
                                "typical_active_hours"
                            ]
                        ),
                        "typical_duration": baseline[
                            "typical_duration"
                        ],
                        "seasonal_pattern": json.dumps(
                            baseline[
                                "seasonal_pattern"
                            ]
                        ),
                        "historical_event_count":
                            baseline[
                                "historical_event_count"
                            ],
                    },
                )

                inserted += 1

                action = "INSERTED"

            else:

                db.execute(
                    text(
                        """
                        UPDATE site_baselines
                        SET
                            baseline_frp =
                                :baseline_frp,
                            frp_std =
                                :frp_std,
                            typical_active_hours =
                                CAST(
                                    :typical_active_hours
                                    AS jsonb
                                ),
                            typical_duration =
                                :typical_duration,
                            seasonal_pattern =
                                CAST(
                                    :seasonal_pattern
                                    AS jsonb
                                ),
                            historical_event_count =
                                :historical_event_count,
                            updated_at = NOW()
                        WHERE facility_id =
                            :facility_id
                        """
                    ),
                    {
                        "facility_id": facility_id,
                        "baseline_frp": baseline[
                            "baseline_frp"
                        ],
                        "frp_std": baseline[
                            "frp_std"
                        ],
                        "typical_active_hours": json.dumps(
                            baseline[
                                "typical_active_hours"
                            ]
                        ),
                        "typical_duration": baseline[
                            "typical_duration"
                        ],
                        "seasonal_pattern": json.dumps(
                            baseline[
                                "seasonal_pattern"
                            ]
                        ),
                        "historical_event_count":
                            baseline[
                                "historical_event_count"
                            ],
                    },
                )

                updated += 1

                action = "UPDATED"

            print(
                f"{action:9} "
                f"{facility_id} | "
                f"events={len(facility_events):4d} | "
                f"baseline_frp="
                f"{baseline['baseline_frp']:.3f} | "
                f"std="
                f"{baseline['frp_std']:.3f}"
            )

        # ---------------------------------------------------------
        # Commit
        # ---------------------------------------------------------

        db.commit()

        # ---------------------------------------------------------
        # Verification
        # ---------------------------------------------------------

        db_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM site_baselines
                """
            )
        ).scalar_one()

        db_event_total = db.execute(
            text(
                """
                SELECT COALESCE(
                    SUM(historical_event_count),
                    0
                )
                FROM site_baselines
                """
            )
        ).scalar_one()

        print("\n" + "=" * 70)
        print("LOAD COMPLETE")
        print("=" * 70)

        print(
            f"Facilities processed:       "
            f"{len(grouped):,}"
        )

        print(
            f"Inserted:                   "
            f"{inserted:,}"
        )

        print(
            f"Updated:                    "
            f"{updated:,}"
        )

        print(
            f"Database baseline rows:     "
            f"{int(db_count):,}"
        )

        print(
            f"Historical events covered:  "
            f"{int(db_event_total):,}"
        )

        print(
            f"Events used for calculation:"
            f" {total_events:,}"
        )

        # ---------------------------------------------------------
        # Verification checks
        # ---------------------------------------------------------

        if int(db_count) < len(grouped):

            raise RuntimeError(
                "Verification failed: not all facilities "
                "have site baselines."
            )

        if int(db_event_total) != total_events:

            raise RuntimeError(
                "Verification failed: historical event "
                "count mismatch."
            )

        print("\nVerification: PASS")
        print("SUCCESS")

    except Exception as exc:

        db.rollback()

        print(
            "\nERROR:",
            str(exc),
            file=sys.stderr,
        )

        sys.exit(1)

    finally:

        db.close()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    load_baselines()