"""
PHOENIX — Bulk load event classifications.

Source:
    thermal_events

Target:
    classifications

The classification is NOT recalculated here.
thermal_events remains the source of truth.

This loader uses classification_id as the conflict key because
the current database schema does NOT have a UNIQUE constraint
on event_id.

Run:

    $env:PYTHONPATH="backend"
    python backend\ingestion\classification\load_classifications.py
"""

from __future__ import annotations

import json
import sys
import uuid
from collections import Counter

from sqlalchemy import text

from db.database import SessionLocal


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

UUID_NAMESPACE = uuid.NAMESPACE_URL


def stable_classification_uuid(event_id: str) -> str:
    """
    Deterministic UUID for each event classification.
    """

    return str(
        uuid.uuid5(
            UUID_NAMESPACE,
            f"phoenix-dahej-classification:{event_id}",
        )
    )


def serialize_reasons(reasons) -> str:
    """
    Convert PostgreSQL JSONB/Python values into valid JSON.
    """

    if reasons is None:
        return "[]"

    if isinstance(reasons, (list, dict)):
        return json.dumps(
            reasons,
            ensure_ascii=False,
        )

    if isinstance(reasons, str):

        try:
            json.loads(reasons)
            return reasons

        except json.JSONDecodeError:
            return json.dumps(
                [reasons],
                ensure_ascii=False,
            )

    return json.dumps(
        [str(reasons)],
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------
# Fetch source classifications
# ---------------------------------------------------------------------

def fetch_classified_events(db):

    result = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                classification,
                classification_confidence,
                classification_reasons
            FROM thermal_events
            WHERE classification IS NOT NULL
            ORDER BY event_id
            """
        )
    )

    return list(result)


# ---------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------

def load_classifications() -> None:

    print("=" * 70)
    print("PHOENIX — BULK LOAD CLASSIFICATIONS")
    print("=" * 70)

    db = SessionLocal()

    try:

        # -------------------------------------------------------------
        # Fetch source
        # -------------------------------------------------------------

        rows = fetch_classified_events(db)

        print(
            f"\nClassified thermal events: "
            f"{len(rows):,}"
        )

        if not rows:
            raise RuntimeError(
                "No classified thermal events found."
            )

        # -------------------------------------------------------------
        # Duplicate validation
        # -------------------------------------------------------------

        event_ids = [
            str(row.event_id)
            for row in rows
        ]

        if len(event_ids) != len(set(event_ids)):

            raise RuntimeError(
                "Duplicate event IDs found in thermal_events."
            )

        print(
            "Duplicate event IDs: 0"
        )

        # -------------------------------------------------------------
        # Distribution
        # -------------------------------------------------------------

        distribution = Counter(
            str(row.classification)
            for row in rows
        )

        print(
            "\nClassification distribution:"
        )

        for classification, count in sorted(
            distribution.items()
        ):
            print(
                f"  {classification}: {count:,}"
            )

        # -------------------------------------------------------------
        # Prepare bulk payload
        # -------------------------------------------------------------

        payload = []

        for row in rows:

            event_id = str(
                row.event_id
            )

            classification = str(
                row.classification
            )

            confidence = (
                float(
                    row.classification_confidence
                )
                if row.classification_confidence
                is not None
                else None
            )

            # ---------------------------------------------------------
            # Validate confidence
            # ---------------------------------------------------------

            if confidence is not None:

                if not 0 <= confidence <= 1:

                    raise ValueError(
                        f"Invalid confidence for "
                        f"{event_id}: {confidence}"
                    )

            # ---------------------------------------------------------
            # Serialize JSONB reasons
            # ---------------------------------------------------------

            reasons_json = serialize_reasons(
                row.classification_reasons
            )

            # Validate JSON before sending to PostgreSQL.
            json.loads(reasons_json)

            payload.append(
                {
                    "classification_id":
                        stable_classification_uuid(
                            event_id
                        ),

                    "event_id":
                        event_id,

                    "classification":
                        classification,

                    "confidence":
                        confidence,

                    "reasons":
                        reasons_json,
                }
            )

        print(
            f"\nPrepared {len(payload):,} rows "
            "for bulk upsert."
        )

        # -------------------------------------------------------------
        # Bulk UPSERT
        # -------------------------------------------------------------
        #
        # IMPORTANT:
        # Current schema has no UNIQUE(event_id).
        #
        # classification_id is the primary/unique identifier,
        # so it is used as the conflict target.
        # -------------------------------------------------------------

        db.execute(
            text(
                """
                INSERT INTO classifications (
                    classification_id,
                    event_id,
                    classification,
                    confidence,
                    reasons,
                    created_at
                )
                SELECT
                    CAST(x.classification_id AS uuid),
                    CAST(x.event_id AS uuid),
                    x.classification,
                    CAST(x.confidence AS double precision),
                    CAST(x.reasons AS jsonb),
                    NOW()
                FROM jsonb_to_recordset(
                    CAST(:payload AS jsonb)
                ) AS x(
                    classification_id text,
                    event_id text,
                    classification text,
                    confidence text,
                    reasons text
                )
                ON CONFLICT (classification_id)
                DO UPDATE SET
                    event_id =
                        EXCLUDED.event_id,
                    classification =
                        EXCLUDED.classification,
                    confidence =
                        EXCLUDED.confidence,
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

        db.commit()

        print(
            "\nBulk upsert committed successfully."
        )

        # -------------------------------------------------------------
        # Verification
        # -------------------------------------------------------------

        db_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM classifications
                """
            )
        ).scalar_one()

        unique_events = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT event_id)
                FROM classifications
                """
            )
        ).scalar_one()

        source_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events
                WHERE classification IS NOT NULL
                """
            )
        ).scalar_one()

        # -------------------------------------------------------------
        # Database distribution
        # -------------------------------------------------------------

        result = db.execute(
            text(
                """
                SELECT
                    classification,
                    COUNT(*) AS count
                FROM classifications
                GROUP BY classification
                ORDER BY classification
                """
            )
        )

        db_distribution = {
            str(row.classification):
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
            f"Source classified events: "
            f"{len(rows):,}"
        )

        print(
            f"Database classification rows: "
            f"{int(db_count):,}"
        )

        print(
            f"Unique classified events: "
            f"{int(unique_events):,}"
        )

        print(
            "\nDatabase distribution:"
        )

        for classification, count in sorted(
            db_distribution.items()
        ):
            print(
                f"  {classification}: {count:,}"
            )

        # -------------------------------------------------------------
        # Verification
        # -------------------------------------------------------------

        if int(db_count) != len(rows):

            raise RuntimeError(
                "Verification failed: database row count "
                "does not match source."
            )

        if int(unique_events) != len(rows):

            raise RuntimeError(
                "Verification failed: unique classified "
                "event count does not match source."
            )

        if int(source_count) != len(rows):

            raise RuntimeError(
                "Verification failed: thermal_events "
                "source count changed unexpectedly."
            )

        if distribution != db_distribution:

            raise RuntimeError(
                "Verification failed: classification "
                "distribution does not match source."
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
    load_classifications()