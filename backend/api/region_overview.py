from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db
from api.map_replay import get_scenario


router = APIRouter(
    prefix="/region",
    tags=["region-overview"],
)


def serialize_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat()

    return str(value)


@router.get("/overview")
def get_region_overview(
    window_id: str = Query("window-3"),
    db: Session = Depends(get_db),
):
    """
    Return the complete intelligence payload required by the
    regional overview screen.

    The frontend receives already-aggregated intelligence rather
    than calculating business metrics itself.
    """

    scenario = get_scenario(window_id)

    data_start = scenario["data_start"]
    data_end = scenario["data_end"]

    # ------------------------------------------------------------
    # Thermal events
    # ------------------------------------------------------------

    event_query = text(
        """
        SELECT
            event_id,
            first_seen,
            latitude,
            longitude,
            classification,
            classification_confidence,
            anomaly_state,
            risk_score,
            severity,
            max_frp
        FROM thermal_events
        WHERE first_seen >= :data_start
          AND first_seen < :data_end
        ORDER BY
            COALESCE(risk_score, 0) DESC,
            first_seen DESC
        """
    )

    event_rows = db.execute(
        event_query,
        {
            "data_start": data_start,
            "data_end": data_end,
        },
    ).mappings().all()

    # ------------------------------------------------------------
    # Raw FIRMS / thermal observations
    # ------------------------------------------------------------

    observation_query = text(
        """
        SELECT COUNT(*) AS count
        FROM thermal_observations
        WHERE timestamp >= :data_start
          AND timestamp < :data_end
        """
    )

    observation_row = db.execute(
        observation_query,
        {
            "data_start": data_start,
            "data_end": data_end,
        },
    ).mappings().one()

    raw_detections = int(
        observation_row["count"] or 0
    )

    # ------------------------------------------------------------
    # Event metrics
    # ------------------------------------------------------------

    high_risk_events = sum(
        1
        for event in event_rows
        if (event["risk_score"] or 0) >= 70
        or str(event["severity"] or "").lower()
        in {"high", "critical"}
    )

    anomalous_sources = sum(
        1
        for event in event_rows
        if str(event["anomaly_state"] or "").lower()
        in {"anomalous", "elevated", "critical"}
    )

    classification_counts = {}

    for event in event_rows:
        classification = event["classification"] or "unknown"

        classification_counts[classification] = (
            classification_counts.get(classification, 0) + 1
        )

    classifications_detected = len(
        [
            value
            for value in classification_counts
            if value != "unknown"
        ]
    )

    frp_values = [
        event["max_frp"]
        for event in event_rows
        if event["max_frp"] is not None
    ]

    average_peak_frp = (
        sum(frp_values) / len(frp_values)
        if frp_values
        else 0
    )

    # ------------------------------------------------------------
    # Priority signals
    # ------------------------------------------------------------

    priority_signals = []

    for event in event_rows[:5]:
        priority_signals.append(
            {
                "event_id": str(event["event_id"]),
                "classification": event["classification"],
                "classification_confidence": event[
                    "classification_confidence"
                ],
                "anomaly_state": event["anomaly_state"],
                "risk_score": event["risk_score"],
                "severity": event["severity"],
                "max_frp": event["max_frp"],
                "first_seen": serialize_datetime(
                    event["first_seen"]
                ),
            }
        )

    # ------------------------------------------------------------
    # Map events
    #
    # Keep this intentionally small. The overview map is a preview,
    # not the full Explore map.
    # ------------------------------------------------------------

    map_events = []

    for event in event_rows[:150]:
        map_events.append(
            {
                "event_id": str(event["event_id"]),
                "latitude": event["latitude"],
                "longitude": event["longitude"],
                "classification": event["classification"],
                "risk_score": event["risk_score"],
            }
        )

    # ------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------

    facility_query = text(
        """
        SELECT
            facility_id,
            name,
            operator,
            facility_type,
            latitude,
            longitude,
            source,
            historical_event_count,
            anomalous_event_count,
            current_risk,
            cumulative_emissions,
            last_incident
        FROM facilities
        ORDER BY
            COALESCE(current_risk, 0) DESC,
            COALESCE(anomalous_event_count, 0) DESC,
            name ASC
        """
    )

    facility_rows = db.execute(
        facility_query
    ).mappings().all()

    facility_watchlist = []

    for facility in facility_rows[:5]:
        facility_watchlist.append(
            {
                "facility_id": str(
                    facility["facility_id"]
                ),
                "name": facility["name"],
                "operator": facility["operator"],
                "facility_type": facility[
                    "facility_type"
                ],
                "current_risk": facility[
                    "current_risk"
                ],
                "anomalous_event_count": facility[
                    "anomalous_event_count"
                ],
                "cumulative_emissions": facility[
                    "cumulative_emissions"
                ],
                "last_incident": serialize_datetime(
                    facility["last_incident"]
                ),
            }
        )

    return {
        "region": "dahej",
        "region_name": "Dahej Industrial Region",

        "window": {
            "id": scenario["id"],
            "label": scenario["label"],
        },

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "pipeline": {
            "raw_detections": raw_detections,
            "thermal_events": len(event_rows),
            "intelligence_classes": classifications_detected,
        },

        "metrics": {
            "high_risk_events": high_risk_events,
            "anomalous_sources": anomalous_sources,
            "monitored_facilities": len(
                facility_rows
            ),
            "average_peak_frp": round(
                average_peak_frp,
                1,
            ),
        },

        "classification_counts": classification_counts,

        "priority_signals": priority_signals,

        "facility_watchlist": facility_watchlist,

        "map_events": map_events,
    }