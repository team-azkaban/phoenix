"""
PHOENIX — Calculate and bulk-load event risk scores.

Source:
    thermal_events

Targets:
    risk_scores
    thermal_events.risk_score
    thermal_events.severity
    thermal_events.risk_reasons

This is a transparent POC rule-based risk model.

Risk score: 0–100

Components:
    1. Thermal intensity / FRP       0–30
    2. Population exposure           0–25
    3. Persistence / duration        0–15
    4. Facility proximity            0–15
    5. Anomaly deviation             0–15

The score is explainable. Each event receives a list of
reasons explaining the contribution.

This script does NOT recalculate classification, emissions,
land cover, weather, or population.

It uses the values already stored in thermal_events.

The loader is idempotent and uses deterministic risk IDs.

Run:

    $env:PYTHONPATH="backend"
    python backend\ingestion\risk\load_risk_scores.py
"""

from __future__ import annotations

import json
import math
import sys
import uuid
from collections import Counter

from sqlalchemy import text

from db.database import SessionLocal


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

UUID_NAMESPACE = uuid.NAMESPACE_URL


def stable_risk_uuid(event_id: str) -> str:
    """
    Deterministic UUID for each event risk score.
    """

    return str(
        uuid.uuid5(
            UUID_NAMESPACE,
            f"phoenix-dahej-risk:{event_id}",
        )
    )


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Restrict a value to a range.
    """

    return max(
        minimum,
        min(value, maximum),
    )


def safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert DB values to float.
    """

    if value is None:
        return default

    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------
# Risk calculation
# ---------------------------------------------------------------------

def calculate_risk(event) -> dict:
    """
    Calculate an explainable 0–100 risk score.

    Components:

        FRP                  0–30
        Population          0–25
        Persistence          0–15
        Facility proximity   0–15
        Anomaly deviation    0–15
    """

    reasons = []

    # -------------------------------------------------------------
    # Read event fields
    # -------------------------------------------------------------

    frp = safe_float(
        event.current_frp
    )

    max_frp = safe_float(
        event.max_frp
    )

    population = safe_float(
        event.population_exposed
    )

    duration = safe_float(
        event.duration
    )

    observation_count = int(
        event.observation_count or 1
    )

    facility_distance = (
        safe_float(
            event.facility_distance_m,
            default=999999.0,
        )
        if event.facility_distance_m is not None
        else 999999.0
    )

    baseline_deviation = safe_float(
        event.baseline_deviation
    )

    classification = (
        str(event.classification)
        if event.classification is not None
        else "unknown"
    )

    anomaly_state = (
        str(event.anomaly_state)
        if event.anomaly_state is not None
        else "unknown"
    )

    # =============================================================
    # 1. THERMAL INTENSITY — 0 to 30
    # =============================================================

    # FRP is heavily right-skewed, so logarithmic scaling prevents
    # extremely large events from completely dominating the score.

    thermal_reference = max(
        frp,
        max_frp,
        0.0,
    )

    frp_component = (
        30.0
        * math.log1p(thermal_reference)
        / math.log1p(100.0)
    )

    frp_component = clamp(
        frp_component,
        0.0,
        30.0,
    )

    reasons.append(
        f"Thermal intensity contributes "
        f"{frp_component:.1f}/30 based on "
        f"FRP of {thermal_reference:.2f} MW."
    )

    # =============================================================
    # 2. POPULATION EXPOSURE — 0 to 25
    # =============================================================

    # Population is also log-scaled because exposure values vary
    # substantially between events.

    population_component = (
        25.0
        * math.log1p(population)
        / math.log1p(1500.0)
    )

    population_component = clamp(
        population_component,
        0.0,
        25.0,
    )

    if population > 0:

        reasons.append(
            f"Estimated population exposure is "
            f"{population:.1f} people, contributing "
            f"{population_component:.1f}/25."
        )

    else:

        reasons.append(
            "No WorldPop population exposure was "
            "estimated within the event exposure radius."
        )

    # =============================================================
    # 3. PERSISTENCE — 0 to 15
    # =============================================================

    # Observation persistence:
    #   1 observation = low persistence
    #   2–4 = moderate
    #   5+ = stronger persistence
    #
    # Duration is incorporated as a secondary signal.

    observation_score = clamp(
        (observation_count - 1) / 9.0,
        0.0,
        1.0,
    )

    duration_score = clamp(
        duration / 24.0,
        0.0,
        1.0,
    )

    persistence_component = (
        15.0
        * (
            0.7 * observation_score
            + 0.3 * duration_score
        )
    )

    persistence_component = clamp(
        persistence_component,
        0.0,
        15.0,
    )

    reasons.append(
        f"Event persistence contributes "
        f"{persistence_component:.1f}/15 from "
        f"{observation_count} observation(s) and "
        f"{duration:.2f} hour(s) duration."
    )

    # =============================================================
    # 4. FACILITY PROXIMITY — 0 to 15
    # =============================================================

    # Only nearby facilities receive meaningful proximity risk.

    if facility_distance <= 500:

        proximity_component = 15.0

    elif facility_distance <= 1000:

        proximity_component = 12.0

    elif facility_distance <= 1500:

        proximity_component = 9.0

    elif facility_distance <= 3000:

        proximity_component = 5.0

    elif facility_distance <= 5000:

        proximity_component = 2.0

    else:

        proximity_component = 0.0

    if facility_distance < 999999:

        reasons.append(
            f"Nearest known facility is "
            f"{facility_distance:.1f} m away, "
            f"contributing "
            f"{proximity_component:.1f}/15."
        )

    else:

        reasons.append(
            "No known facility proximity signal "
            "is available."
        )

    # =============================================================
    # 5. ANOMALY — 0 to 15
    # =============================================================

    # baseline_deviation is expected to represent deviation from
    # the facility's historical baseline.
    #
    # If it is unavailable, anomaly_state is used as a fallback.

    if baseline_deviation > 0:

        anomaly_component = (
            15.0
            * clamp(
                baseline_deviation / 3.0,
                0.0,
                1.0,
            )
        )

        anomaly_component = clamp(
            anomaly_component,
            0.0,
            15.0,
        )

        reasons.append(
            f"Baseline deviation of "
            f"{baseline_deviation:.2f} contributes "
            f"{anomaly_component:.1f}/15."
        )

    elif anomaly_state.lower() in {
        "anomalous",
        "high",
        "elevated",
    }:

        anomaly_component = 12.0

        reasons.append(
            "Event is marked anomalous/elevated, "
            "contributing 12.0/15."
        )

    elif anomaly_state.lower() in {
        "persistent",
    }:

        anomaly_component = 8.0

        reasons.append(
            "Event is marked persistent, "
            "contributing 8.0/15."
        )

    else:

        anomaly_component = 0.0

        reasons.append(
            "No positive anomaly-deviation signal "
            "is available."
        )

    # =============================================================
    # Total
    # =============================================================

    raw_score = (
        frp_component
        + population_component
        + persistence_component
        + proximity_component
        + anomaly_component
    )

    risk_score = clamp(
        raw_score,
        0.0,
        100.0,
    )

    risk_score = round(
        risk_score,
        2,
    )

    # =============================================================
    # Severity
    # =============================================================

    if risk_score >= 75:

        severity = "critical"

    elif risk_score >= 50:

        severity = "high"

    elif risk_score >= 25:

        severity = "medium"

    else:

        severity = "low"

    reasons.append(
        f"Final risk score is {risk_score:.2f}/100, "
        f"assigned severity '{severity}'."
    )

    # Classification context
    reasons.append(
        f"Event classification is "
        f"'{classification}'."
    )

    return {
        "risk_score": risk_score,
        "severity": severity,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------
# Fetch events
# ---------------------------------------------------------------------

def fetch_events(db):

    result = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                current_frp,
                max_frp,
                population_exposed,
                duration,
                observation_count,
                facility_distance_m,
                baseline_deviation,
                anomaly_state,
                classification
            FROM thermal_events
            ORDER BY event_id
            """
        )
    )

    return list(result)


# ---------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------

def load_risk_scores() -> None:

    print("=" * 70)
    print("PHOENIX — BULK LOAD RISK SCORES")
    print("=" * 70)

    db = SessionLocal()

    try:

        # -------------------------------------------------------------
        # Fetch events
        # -------------------------------------------------------------

        events = fetch_events(db)

        print(
            f"\nThermal events: "
            f"{len(events):,}"
        )

        if not events:

            raise RuntimeError(
                "No thermal events found."
            )

        # -------------------------------------------------------------
        # Prepare payload
        # -------------------------------------------------------------

        payload = []

        severity_distribution = Counter()

        for event in events:

            calculated = calculate_risk(
                event
            )

            severity = calculated[
                "severity"
            ]

            severity_distribution[
                severity
            ] += 1

            payload.append(
                {
                    "risk_id":
                        stable_risk_uuid(
                            str(event.event_id)
                        ),

                    "event_id":
                        str(event.event_id),

                    "risk_score":
                        calculated[
                            "risk_score"
                        ],

                    "severity":
                        severity,

                    "reasons":
                        json.dumps(
                            calculated[
                                "reasons"
                            ],
                            ensure_ascii=False,
                        ),
                }
            )

        print(
            f"Prepared {len(payload):,} "
            "risk-score records."
        )

        # -------------------------------------------------------------
        # Severity distribution
        # -------------------------------------------------------------

        print(
            "\nCalculated severity distribution:"
        )

        for severity, count in sorted(
            severity_distribution.items()
        ):

            print(
                f"  {severity}: {count:,}"
            )

        # -------------------------------------------------------------
        # BULK UPSERT risk_scores
        # -------------------------------------------------------------

        db.execute(
            text(
                """
                INSERT INTO risk_scores (
                    risk_id,
                    event_id,
                    risk_score,
                    severity,
                    reasons,
                    created_at
                )
                SELECT
                    CAST(x.risk_id AS uuid),
                    CAST(x.event_id AS uuid),
                    CAST(x.risk_score AS double precision),
                    x.severity,
                    CAST(x.reasons AS jsonb),
                    NOW()
                FROM jsonb_to_recordset(
                    CAST(:payload AS jsonb)
                ) AS x(
                    risk_id text,
                    event_id text,
                    risk_score text,
                    severity text,
                    reasons text
                )
                ON CONFLICT (risk_id)
                DO UPDATE SET
                    event_id =
                        EXCLUDED.event_id,
                    risk_score =
                        EXCLUDED.risk_score,
                    severity =
                        EXCLUDED.severity,
                    reasons =
                        EXCLUDED.reasons
                """
            ),
            {
                "payload": json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            },
        )

        # -------------------------------------------------------------
        # Update thermal_events in bulk
        # -------------------------------------------------------------

        db.execute(
            text(
                """
                UPDATE thermal_events AS t
                SET
                    risk_score =
                        CAST(x.risk_score AS double precision),
                    severity =
                        x.severity,
                    risk_reasons =
                        CAST(x.reasons AS jsonb),
                    updated_at =
                        NOW()
                FROM jsonb_to_recordset(
                    CAST(:payload AS jsonb)
                ) AS x(
                    event_id text,
                    risk_score text,
                    severity text,
                    reasons text
                )
                WHERE t.event_id =
                    CAST(x.event_id AS uuid)
                """
            ),
            {
                "payload": json.dumps(
                    [
                        {
                            "event_id":
                                row["event_id"],
                            "risk_score":
                                row["risk_score"],
                            "severity":
                                row["severity"],
                            "reasons":
                                row["reasons"],
                        }
                        for row in payload
                    ],
                    ensure_ascii=False,
                )
            },
        )

        # -------------------------------------------------------------
        # Commit
        # -------------------------------------------------------------

        db.commit()

        print(
            "\nBulk risk-score load committed successfully."
        )

        # -------------------------------------------------------------
        # Verification
        # -------------------------------------------------------------

        risk_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM risk_scores
                """
            )
        ).scalar_one()

        thermal_risk_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events
                WHERE risk_score IS NOT NULL
                """
            )
        ).scalar_one()

        unique_risk_events = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT event_id)
                FROM risk_scores
                """
            )
        ).scalar_one()

        # -------------------------------------------------------------
        # Verify severity distribution in risk_scores
        # -------------------------------------------------------------

        result = db.execute(
            text(
                """
                SELECT
                    severity,
                    COUNT(*) AS count
                FROM risk_scores
                GROUP BY severity
                ORDER BY severity
                """
            )
        )

        db_distribution = {
            str(row.severity):
                int(row.count)
            for row in result
        }

        # -------------------------------------------------------------
        # Output
        # -------------------------------------------------------------

        print("\n" + "=" * 70)
        print("LOAD COMPLETE")
        print("=" * 70)

        print(
            f"Thermal events processed: "
            f"{len(events):,}"
        )

        print(
            f"Risk-score rows:           "
            f"{int(risk_count):,}"
        )

        print(
            f"Events with risk score:    "
            f"{int(thermal_risk_count):,}"
        )

        print(
            f"Unique risk events:        "
            f"{int(unique_risk_events):,}"
        )

        print(
            "\nDatabase severity distribution:"
        )

        for severity, count in sorted(
            db_distribution.items()
        ):

            print(
                f"  {severity}: {count:,}"
            )

        # -------------------------------------------------------------
        # Verification
        # -------------------------------------------------------------

        if int(risk_count) != len(events):

            raise RuntimeError(
                "Verification failed: risk_scores "
                "count does not match thermal_events."
            )

        if int(unique_risk_events) != len(events):

            raise RuntimeError(
                "Verification failed: duplicate or "
                "missing risk events."
            )

        if int(thermal_risk_count) != len(events):

            raise RuntimeError(
                "Verification failed: not every thermal "
                "event received a risk score."
            )

        if severity_distribution != db_distribution:

            raise RuntimeError(
                "Verification failed: severity distribution "
                "does not match calculated distribution."
            )

        print(
            "\nVerification: PASS"
        )

        print(
            "SUCCESS"
        )

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
    load_risk_scores()