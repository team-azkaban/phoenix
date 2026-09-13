from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db
from api.map_replay import REPLAY_SCENARIOS


router = APIRouter(
    prefix="/map/events",
    tags=["map-events"],
)


def get_scenario(scenario_id: str):
    for scenario in REPLAY_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario

    raise HTTPException(
        status_code=404,
        detail="Window not found.",
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
def get_map_events(
    window_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get events for a POC window.

    window_id is NOT a date.

    The backend resolves it to one of the predefined
    historical Supabase windows.
    """

    scenario = get_scenario(window_id)

    query = text(
        """
        SELECT
            event_id,
            first_seen,
            last_seen,

            latitude,
            longitude,

            observation_count,

            facility_id,
            facility_distance_m,
            facility_type,

            landcover_class,
            built_up_fraction,
            forest_fraction,
            cropland_fraction,

            current_frp,
            max_frp,
            mean_frp,
            duration,

            baseline_frp,
            baseline_deviation,
            anomaly_state,

            classification,
            classification_confidence,
            classification_reasons,

            emissions_estimate,
            population_exposed,

            wind_speed,
            wind_direction,

            spread_geometry,

            risk_score,
            severity,
            risk_reasons,

            alert_status,
            alert_reasons,

            ST_AsGeoJSON(geometry)::json AS geometry_geojson,

            CASE
                WHEN spread_geometry IS NOT NULL
                THEN ST_AsGeoJSON(spread_geometry)::json
                ELSE NULL
            END AS spread_geojson

        FROM thermal_events

        WHERE first_seen >= :data_start
          AND first_seen < :data_end

        ORDER BY
            first_seen ASC,
            max_frp DESC
        """
    )

    rows = db.execute(
        query,
        {
            "data_start": scenario["data_start"],
            "data_end": scenario["data_end"],
        },
    ).mappings().all()

    events = []

    for row in rows:
        events.append(
            {
                "event_id": str(row["event_id"]),

                "first_seen": serialize_datetime(
                    row["first_seen"]
                ),

                "last_seen": serialize_datetime(
                    row["last_seen"]
                ),

                "latitude": row["latitude"],
                "longitude": row["longitude"],

                "observation_count": row[
                    "observation_count"
                ],

                "facility_id": (
                    str(row["facility_id"])
                    if row["facility_id"]
                    else None
                ),

                "facility_distance_m": row[
                    "facility_distance_m"
                ],

                "facility_type": row["facility_type"],

                "landcover_class": row[
                    "landcover_class"
                ],

                "built_up_fraction": row[
                    "built_up_fraction"
                ],

                "forest_fraction": row[
                    "forest_fraction"
                ],

                "cropland_fraction": row[
                    "cropland_fraction"
                ],

                "current_frp": row["current_frp"],
                "max_frp": row["max_frp"],
                "mean_frp": row["mean_frp"],
                "duration": row["duration"],

                "baseline_frp": row["baseline_frp"],
                "baseline_deviation": row[
                    "baseline_deviation"
                ],

                "anomaly_state": row[
                    "anomaly_state"
                ],

                "classification": row[
                    "classification"
                ],

                "classification_confidence": row[
                    "classification_confidence"
                ],

                "classification_reasons": row[
                    "classification_reasons"
                ],

                "emissions_estimate": row[
                    "emissions_estimate"
                ],

                "population_exposed": row[
                    "population_exposed"
                ],

                "wind_speed": row["wind_speed"],
                "wind_direction": row[
                    "wind_direction"
                ],

                "risk_score": row["risk_score"],
                "severity": row["severity"],

                "risk_reasons": row[
                    "risk_reasons"
                ],

                "alert_status": row[
                    "alert_status"
                ],

                "alert_reasons": row[
                    "alert_reasons"
                ],

                "geometry": row[
                    "geometry_geojson"
                ],

                "spread_geometry": row[
                    "spread_geojson"
                ],
            }
        )

    return {
        "region": "dahej",
        "count": len(events),
        "events": events,
    }