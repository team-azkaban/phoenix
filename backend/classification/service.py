from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from db.database import SessionLocal
from classification.rules import classify_event


def classify_all_events() -> None:

    db = SessionLocal()

    try:
        events = db.execute(
            text(
                """
                SELECT
                    event_id,
                    facility_type,
                    facility_distance_m,
                    observation_count,
                    duration,
                    max_frp,
                    current_frp
                FROM thermal_events
                ORDER BY first_seen
                """
            )
        ).mappings().all()

        print(
            f"Events loaded: {len(events):,}"
        )

        update_sql = text(
            """
            UPDATE thermal_events
            SET
                classification = :classification,
                classification_confidence = :confidence,
                classification_reasons = CAST(
                    :reasons AS jsonb
                ),
                updated_at = now()
            WHERE event_id = :event_id
            """
        )

        counts: dict[str, int] = {}

        for index, event in enumerate(events, start=1):

            result = classify_event(
                facility_type=event["facility_type"],
                facility_distance_m=event[
                    "facility_distance_m"
                ],
                observation_count=event[
                    "observation_count"
                ],
                duration_hours=event["duration"],
                max_frp=event["max_frp"],
                current_frp=event["current_frp"],
            )

            db.execute(
                update_sql,
                {
                    "event_id": event["event_id"],
                    "classification": result.classification,
                    "confidence": result.confidence,
                    "reasons": json.dumps(
                        result.reasons
                    ),
                },
            )

            counts[result.classification] = (
                counts.get(result.classification, 0)
                + 1
            )

            if index % 250 == 0:
                db.commit()
                print(
                    f"  Classified "
                    f"{index:,}/{len(events):,}"
                )

        db.commit()

        print("\nClassification complete.")

        print("\nClassification distribution:")

        for label, count in sorted(
            counts.items(),
            key=lambda item: -item[1],
        ):
            print(
                f"  {label:22s} {count:,}"
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    classify_all_events()