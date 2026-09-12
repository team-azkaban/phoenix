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
        # ----------------------------------------------------------------
        # Load all event evidence required by the rule-based classifier.
        #
        # Flare/mining context is determined spatially from the context
        # tables already loaded into Supabase.
        # ----------------------------------------------------------------

        events = db.execute(
            text(
                """
                SELECT
                    te.event_id,
                    te.facility_type,
                    te.facility_distance_m,
                    te.observation_count,
                    te.duration,
                    te.max_frp,
                    te.current_frp,

                    te.landcover_class,
                    te.cropland_fraction,
                    te.forest_fraction,
                    te.built_up_fraction,

                    COALESCE(
                        (
                            SELECT MIN(
                                ST_Distance(
                                    ST_SetSRID(
                                        ST_MakePoint(
                                            te.longitude,
                                            te.latitude
                                        ),
                                        4326
                                    )::geography,
                                    ST_SetSRID(
                                        ST_MakePoint(
                                            fc.longitude,
                                            fc.latitude
                                        ),
                                        4326
                                    )::geography
                                )
                            )
                            FROM flare_context fc
                            WHERE ST_DWithin(
                                ST_SetSRID(
                                    ST_MakePoint(
                                        te.longitude,
                                        te.latitude
                                    ),
                                    4326
                                )::geography,
                                ST_SetSRID(
                                    ST_MakePoint(
                                        fc.longitude,
                                        fc.latitude
                                    ),
                                    4326
                                )::geography,
                                fc.context_radius_m
                            )
                        ),
                        NULL
                    ) AS flare_distance_m,

                    EXISTS(
                        SELECT 1
                        FROM flare_context fc
                        WHERE ST_DWithin(
                            ST_SetSRID(
                                ST_MakePoint(
                                    te.longitude,
                                    te.latitude
                                ),
                                4326
                            )::geography,
                            ST_SetSRID(
                                ST_MakePoint(
                                    fc.longitude,
                                    fc.latitude
                                ),
                                4326
                            )::geography,
                            fc.context_radius_m
                        )
                    ) AS has_flare_context,

                    COALESCE(
                        (
                            SELECT MIN(
                                ST_Distance(
                                    ST_SetSRID(
                                        ST_MakePoint(
                                            te.longitude,
                                            te.latitude
                                        ),
                                        4326
                                    )::geography,
                                    ST_SetSRID(
                                        ST_MakePoint(
                                            mc.longitude,
                                            mc.latitude
                                        ),
                                        4326
                                    )::geography
                                )
                            )
                            FROM mining_context mc
                            WHERE ST_DWithin(
                                ST_SetSRID(
                                    ST_MakePoint(
                                        te.longitude,
                                        te.latitude
                                    ),
                                    4326
                                )::geography,
                                ST_SetSRID(
                                    ST_MakePoint(
                                        mc.longitude,
                                        mc.latitude
                                    ),
                                    4326
                                )::geography,
                                mc.context_radius_m
                            )
                        ),
                        NULL
                    ) AS mining_distance_m,

                    EXISTS(
                        SELECT 1
                        FROM mining_context mc
                        WHERE ST_DWithin(
                            ST_SetSRID(
                                ST_MakePoint(
                                    te.longitude,
                                    te.latitude
                                ),
                                4326
                            )::geography,
                            ST_SetSRID(
                                ST_MakePoint(
                                    mc.longitude,
                                    mc.latitude
                                ),
                                4326
                            )::geography,
                            mc.context_radius_m
                        )
                    ) AS has_mining_context

                FROM thermal_events te

                ORDER BY te.first_seen
                """
            )
        ).mappings().all()

        print(
            f"Events loaded: {len(events):,}"
        )

        # ----------------------------------------------------------------
        # Update SQL
        # ----------------------------------------------------------------

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

        flare_count = 0
        mining_count = 0

        # ----------------------------------------------------------------
        # Rule-based classification
        # ----------------------------------------------------------------

        for index, event in enumerate(
            events,
            start=1,
        ):
            if event["has_flare_context"]:
                flare_count += 1

            if event["has_mining_context"]:
                mining_count += 1

            result = classify_event(
                facility_type=event["facility_type"],
                facility_distance_m=event[
                    "facility_distance_m"
                ],
                observation_count=event[
                    "observation_count"
                ],
                duration_hours=event[
                    "duration"
                ],
                max_frp=event[
                    "max_frp"
                ],
                current_frp=event[
                    "current_frp"
                ],
                landcover_class=event[
                    "landcover_class"
                ],
                cropland_fraction=event[
                    "cropland_fraction"
                ],
                forest_fraction=event[
                    "forest_fraction"
                ],
                built_up_fraction=event[
                    "built_up_fraction"
                ],
                has_flare_context=bool(
                    event["has_flare_context"]
                ),
                flare_distance_m=event[
                    "flare_distance_m"
                ],
                has_mining_context=bool(
                    event["has_mining_context"]
                ),
                mining_distance_m=event[
                    "mining_distance_m"
                ],
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
                counts.get(
                    result.classification,
                    0,
                )
                + 1
            )

            if index % 250 == 0:
                db.commit()

                print(
                    f"  Classified "
                    f"{index:,}/{len(events):,}"
                )

        # ----------------------------------------------------------------
        # Final commit
        # ----------------------------------------------------------------

        db.commit()

        print("\nClassification complete.")

        print(
            f"\nEvents with flare context: "
            f"{flare_count:,}"
        )

        print(
            f"Events with mining context: "
            f"{mining_count:,}"
        )

        print("\nClassification distribution:")

        for label, count in sorted(
            counts.items(),
            key=lambda item: -item[1],
        ):
            print(
                f"  {label:24s} {count:,}"
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    classify_all_events()