from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db
from services.facility_intelligence import (
    get_facility_environment,
    get_facility_event_map,
    get_facility_concern,
    get_all_facility_concerns,
)


router = APIRouter(
    prefix="/facilities",
    tags=["facilities"],
)


def serialize_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat()

    return str(value)


@router.get("")
def get_facilities(
    db: Session = Depends(get_db),
):
    """
    Get all facilities available for PHOENIX.

    Facility coordinates come directly from the
    authoritative facilities table.
    """

    query = text(
        """
        SELECT
            f.facility_id,
            f.name,
            f.operator,
            f.facility_type,
            f.latitude,
            f.longitude,
            f.source,
            COALESCE(
                sb.historical_event_count,
                COUNT(te.event_id) FILTER (
                    WHERE te.mean_frp IS NOT NULL
                ),
                0
            ) AS historical_event_count,
            f.anomalous_event_count,
            f.current_risk,
            f.cumulative_emissions,
            f.last_incident,
            sb.baseline_frp,
            sb.frp_std,
            sb.typical_active_hours,
            sb.typical_duration,
            sb.seasonal_pattern,
            COALESCE(states.anomaly_state, 'UNKNOWN') AS anomaly_state,
            CASE
                WHEN sb.facility_id IS NULL
                    THEN 'NO_BASELINE_AVAILABLE'
                WHEN sb.historical_event_count < 3
                    THEN 'INSUFFICIENT_HISTORY'
                ELSE 'READY'
            END AS baseline_status
        FROM facilities AS f
        LEFT JOIN site_baselines AS sb
            ON sb.facility_id = f.facility_id
        LEFT JOIN thermal_events AS te
            ON te.facility_id = f.facility_id
        LEFT JOIN (
            SELECT facility_id, anomaly_state
            FROM (
                SELECT
                    facility_id,
                    anomaly_state,
                    COUNT(*) AS state_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY facility_id
                        ORDER BY
                            COUNT(*) DESC,
                            CASE anomaly_state
                                WHEN 'ANOMALOUS' THEN 1
                                WHEN 'PERSISTENT' THEN 2
                                WHEN 'ROUTINE' THEN 3
                                ELSE 4
                            END
                    ) AS state_rank
                FROM thermal_events
                WHERE anomaly_state IS NOT NULL
                GROUP BY facility_id, anomaly_state
            ) ranked_states
            WHERE state_rank = 1
        ) AS states
            ON states.facility_id = f.facility_id
        GROUP BY
            f.facility_id,
            f.name,
            f.operator,
            f.facility_type,
            f.latitude,
            f.longitude,
            f.source,
            f.anomalous_event_count,
            f.current_risk,
            f.cumulative_emissions,
            f.last_incident,
            sb.facility_id,
            sb.historical_event_count,
            sb.baseline_frp,
            sb.frp_std,
            sb.typical_active_hours,
            sb.typical_duration,
            sb.seasonal_pattern,
            states.anomaly_state
        ORDER BY f.name ASC
        """
    )

    rows = db.execute(query).mappings().all()

    facilities = []

    for row in rows:
        facilities.append(
            {
                "facility_id": str(
                    row["facility_id"]
                ),

                "name": row["name"],
                "operator": row["operator"],
                "facility_type": row[
                    "facility_type"
                ],

                "latitude": row["latitude"],
                "longitude": row["longitude"],

                "source": row["source"],

                "historical_event_count": row["historical_event_count"],

                "anomalous_event_count": row[
                    "anomalous_event_count"
                ],

                "current_risk": row[
                    "current_risk"
                ],

                "cumulative_emissions": row[
                    "cumulative_emissions"
                ],

                "last_incident": serialize_datetime(
                    row["last_incident"]
                ),

                "baseline_status": row["baseline_status"],
                "baseline_frp": row["baseline_frp"],
                "frp_std": row["frp_std"],
                "typical_active_hours": row[
                    "typical_active_hours"
                ],
                "typical_duration": row["typical_duration"],
                "seasonal_pattern": row["seasonal_pattern"],
                "anomaly_state": row["anomaly_state"],
            }
        )

    concerns = get_all_facility_concerns(db)
    for facility in facilities:
        concern = concerns.get(
            facility["facility_id"],
            {"state": "INSUFFICIENT_DATA", "score": None, "level": None, "statement": None},
        )
        facility["concern_state"] = concern["state"]
        facility["concern_score"] = concern["score"]
        facility["concern_level"] = concern["level"]
        facility["concern_statement"] = concern.get("statement")

    return {
        "count": len(facilities),
        "facilities": facilities,
    }


@router.get("/{facility_id}/baseline")
def get_facility_baseline(
    facility_id: UUID,
    db: Session = Depends(get_db),
):
    """Return a facility baseline with an explicit data-sufficiency state."""
    query = text(
        """
        SELECT
            f.facility_id,
            f.name,
            COUNT(te.event_id) FILTER (
                WHERE te.mean_frp IS NOT NULL
            ) AS event_count,
            sb.baseline_frp,
            sb.frp_std,
            sb.typical_active_hours,
            sb.typical_duration,
            sb.seasonal_pattern,
            sb.historical_event_count
        FROM facilities AS f
        LEFT JOIN thermal_events AS te
            ON te.facility_id = f.facility_id
        LEFT JOIN site_baselines AS sb
            ON sb.facility_id = f.facility_id
        WHERE f.facility_id = :facility_id
        GROUP BY
            f.facility_id,
            f.name,
            sb.baseline_frp,
            sb.frp_std,
            sb.typical_active_hours,
            sb.typical_duration,
            sb.seasonal_pattern,
            sb.historical_event_count
        """
    )
    row = db.execute(
        query,
        {"facility_id": str(facility_id)},
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Facility not found")

    event_count = int(row["event_count"] or 0)
    stored_count = row["historical_event_count"]

    if stored_count is None:
        status = "NO_BASELINE_AVAILABLE"
        historical_event_count = event_count
    else:
        historical_event_count = int(stored_count)
        status = (
            "INSUFFICIENT_HISTORY"
            if historical_event_count < 3
            else "READY"
        )

    return {
        "facility_id": str(row["facility_id"]),
        "facility_name": row["name"],
        "status": status,
        "historical_event_count": historical_event_count,
        "baseline_frp": row["baseline_frp"],
        "frp_std": row["frp_std"],
        "typical_active_hours": row["typical_active_hours"],
        "typical_duration": row["typical_duration"],
        "seasonal_pattern": row["seasonal_pattern"],
    }


@router.get("/{facility_id}/latest-event")
def get_latest_facility_event(
    facility_id: UUID,
    db: Session = Depends(get_db),
):
    """Return the latest classified event and its explainable signals."""
    query = text(
        """
        SELECT
            f.name AS facility_name,
            e.event_id,
            e.first_seen,
            e.anomaly_state,
            e.current_frp,
            e.mean_frp,
            e.baseline_frp,
            e.baseline_deviation,
            e.classification_reasons
        FROM facilities AS f
        LEFT JOIN LATERAL (
            SELECT
                event_id,
                first_seen,
                anomaly_state,
                current_frp,
                mean_frp,
                baseline_frp,
                baseline_deviation,
                classification_reasons
            FROM thermal_events
            WHERE facility_id = f.facility_id
              AND anomaly_state IS NOT NULL
            ORDER BY first_seen DESC
            LIMIT 1
        ) AS e ON TRUE
        WHERE f.facility_id = :facility_id
        """
    )
    row = db.execute(
        query,
        {"facility_id": str(facility_id)},
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Facility not found")

    payload = row["classification_reasons"] or {}
    if isinstance(payload, list):
        payload = {"explanation": None, "reasons": payload}

    return {
        "facility_id": str(facility_id),
        "facility_name": row["facility_name"],
        "event_id": str(row["event_id"]) if row["event_id"] else None,
        "first_seen": serialize_datetime(row["first_seen"]),
        "anomaly_state": row["anomaly_state"],
        "current_frp": row["current_frp"],
        "mean_frp": row["mean_frp"],
        "baseline_frp": row["baseline_frp"],
        "baseline_deviation": row["baseline_deviation"],
        "event_context": {
            "first_seen": payload.get("event_context", {}).get("first_seen"),
            "duration": payload.get("event_context", {}).get("duration"),
            "facility_distance_m": payload.get("event_context", {}).get(
                "facility_distance_m"
            ),
        },
        "explanation": payload.get("explanation"),
        "reasons": payload.get("reasons", []),
    }


@router.get("/{facility_id}/events/map")
def get_facility_events_map(
    facility_id: UUID,
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    result = get_facility_event_map(
        db,
        str(facility_id),
        start_date=start_date,
        end_date=end_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return result


@router.get("/{facility_id}/environment")
def get_facility_environment_endpoint(
    facility_id: UUID,
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return facility emissions trend + relative environmental status.

    start_date/end_date are optional and, when provided, restrict which
    events' emissions are counted - this is what lets the frontend keep the
    emissions view in sync with whatever period the spatial map is currently
    filtered to.
    """
    result = get_facility_environment(
        db,
        str(facility_id),
        start_date=start_date,
        end_date=end_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return result


@router.get("/{facility_id}/concern")
def get_facility_concern_endpoint(
    facility_id: UUID,
    db: Session = Depends(get_db),
):
    result = get_facility_concern(db, str(facility_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return result