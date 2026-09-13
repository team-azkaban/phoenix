"""
PHOENIX — Populate event-level baseline anomaly values.

Calculates:
    z = (mean_frp - baseline_frp) / frp_std

Writes:
    thermal_events.baseline_deviation
    thermal_events.anomaly_state
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text


# -------------------------------------------------------------
# Load backend/.env
# -------------------------------------------------------------

BACKEND = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND / ".env"

if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        os.environ.setdefault(
            key.strip(),
            value.strip().strip('"').strip("'"),
        )


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not found in backend/.env"
    )


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------

def main() -> None:

    print("=" * 70)
    print("PHOENIX — POPULATE EVENT ANOMALIES")
    print("=" * 70)

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    try:

        with engine.begin() as conn:

            print("Calculating and updating events...")

            result = conn.execute(
                text(
                    """
                    UPDATE thermal_events AS e
                    SET
                        baseline_deviation =
                            ROUND(
                                (
                                    (
                                        e.mean_frp
                                        - sb.baseline_frp
                                    ) / sb.frp_std
                                )::numeric,
                                6
                            )::double precision,

                        anomaly_state =
                            CASE
                                WHEN (
                                    e.mean_frp
                                    - sb.baseline_frp
                                ) / sb.frp_std >= 2.0
                                    THEN 'anomalous'

                                WHEN (
                                    e.mean_frp
                                    - sb.baseline_frp
                                ) / sb.frp_std >= 1.0
                                    THEN 'elevated'

                                ELSE 'normal'
                            END,

                        updated_at = NOW()

                    FROM site_baselines AS sb

                    WHERE e.facility_id = sb.facility_id

                      AND e.facility_id IS NOT NULL

                      AND e.mean_frp IS NOT NULL

                      AND sb.baseline_frp IS NOT NULL

                      AND sb.frp_std IS NOT NULL

                      AND sb.frp_std > 0

                      AND sb.historical_event_count >= 2
                    """
                )
            )

            print(
                f"Events updated: {result.rowcount}"
            )

            # ---------------------------------------------------------
            # Clear values where no valid baseline exists.
            # ---------------------------------------------------------

            conn.execute(
                text(
                    """
                    UPDATE thermal_events AS e
                    SET
                        baseline_deviation = NULL,
                        anomaly_state = NULL,
                        updated_at = NOW()

                    WHERE
                        e.facility_id IS NULL

                        OR e.mean_frp IS NULL

                        OR NOT EXISTS (
                            SELECT 1
                            FROM site_baselines AS sb
                            WHERE sb.facility_id = e.facility_id
                              AND sb.baseline_frp IS NOT NULL
                              AND sb.frp_std IS NOT NULL
                              AND sb.frp_std > 0
                              AND sb.historical_event_count >= 2
                        )
                    """
                )
            )

            # ---------------------------------------------------------
            # Summary
            # ---------------------------------------------------------

            summary = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE anomaly_state = 'normal'
                        ) AS normal,

                        COUNT(*) FILTER (
                            WHERE anomaly_state = 'elevated'
                        ) AS elevated,

                        COUNT(*) FILTER (
                            WHERE anomaly_state = 'anomalous'
                        ) AS anomalous,

                        COUNT(*) FILTER (
                            WHERE baseline_deviation IS NOT NULL
                        ) AS populated

                    FROM thermal_events
                    """
                )
            ).mappings().one()

        print()
        print("-" * 70)
        print("UPDATE COMPLETE")
        print("-" * 70)

        print(
            f"Baseline values populated:  {summary['populated']}"
        )
        print(
            f"Normal:                     {summary['normal']}"
        )
        print(
            f"Elevated:                   {summary['elevated']}"
        )
        print(
            f"Anomalous:                  {summary['anomalous']}"
        )

        print("=" * 70)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()