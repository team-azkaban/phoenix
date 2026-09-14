"""Reusable facility intelligence calculations and persistence helpers."""

from __future__ import annotations

import json
import math
import statistics
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


MIN_BASELINE_EVENTS = 3
PERSISTENT_HISTORY_EVENTS = 6
FRP_STRONG_DEVIATION = 2.0
FRP_SUPPORTING_DEVIATION = 1.0
SIGNAL_DEVIATION = 1.0
TIMING_RARITY = 0.1
FAR_EVENT_DISTANCE_M = 2_000.0
BASELINE_UUID_NAMESPACE = uuid.NAMESPACE_URL


def stable_baseline_uuid(facility_id: str) -> str:
    """Return the deterministic identifier used by the rerunnable loader."""
    return str(
        uuid.uuid5(
            BASELINE_UUID_NAMESPACE,
            f"phoenix-dahej-baseline:{facility_id}",
        )
    )


def _event_timestamp(event: dict[str, Any]) -> datetime | None:
    value = event.get("first_seen")
    return value if isinstance(value, datetime) else None


def calculate_baseline(
    facility_events: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate one facility baseline from events with usable mean FRP."""
    events = [
        event
        for event in facility_events
        if event.get("mean_frp") is not None
    ]
    historical_event_count = len(events)

    if historical_event_count < MIN_BASELINE_EVENTS:
        return {
            "baseline_frp": None,
            "frp_std": None,
            "typical_active_hours": {},
            "typical_duration": None,
            "seasonal_pattern": {},
            "historical_event_count": historical_event_count,
            "status": "INSUFFICIENT_HISTORY",
        }

    frps = [float(event["mean_frp"]) for event in events]
    durations = [
        float(event["duration"])
        for event in events
        if event.get("duration") is not None and event["duration"] >= 0
    ]

    hour_counts = Counter(
        timestamp.hour
        for event in events
        if (timestamp := _event_timestamp(event)) is not None
    )
    hour_total = sum(hour_counts.values())
    typical_active_hours = {
        str(hour): round(count / hour_total, 6)
        for hour, count in sorted(hour_counts.items())
    }

    monthly_values: dict[int, list[float]] = defaultdict(list)
    for event in events:
        timestamp = _event_timestamp(event)
        if timestamp is not None:
            monthly_values[timestamp.month].append(float(event["mean_frp"]))

    seasonal_pattern = {
        str(month): {
            "event_count": len(month_frps),
            "average_frp": round(statistics.mean(month_frps), 6),
        }
        for month, month_frps in sorted(monthly_values.items())
    }

    return {
        "baseline_frp": round(statistics.median(frps), 6),
        "frp_std": round(statistics.stdev(frps), 6),
        "typical_active_hours": typical_active_hours,
        "typical_duration": (
            round(statistics.median(durations), 6) if durations else None
        ),
        "seasonal_pattern": seasonal_pattern,
        "historical_event_count": historical_event_count,
        "status": "READY",
    }


def fetch_facility_events(db: Session) -> list[dict[str, Any]]:
    """Fetch facility-linked events used to build behavioral baselines."""
    result = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                facility_id::text AS facility_id,
                first_seen,
                mean_frp,
                duration
            FROM thermal_events
                        WHERE facility_id IS NOT NULL
            ORDER BY facility_id, first_seen
            """
        )
    )

    return [
        {
            "event_id": str(row.event_id),
            "facility_id": str(row.facility_id),
            "first_seen": row.first_seen,
            "mean_frp": (
                float(row.mean_frp) if row.mean_frp is not None else None
            ),
            "duration": (
                float(row.duration) if row.duration is not None else None
            ),
        }
        for row in result
    ]


def upsert_baselines(db: Session) -> dict[str, int]:
    """Calculate and upsert one baseline row per facility with usable events."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in fetch_facility_events(db):
        grouped[event["facility_id"]].append(event)

    for facility_id, events in grouped.items():
        baseline = calculate_baseline(events)
        payload = {
            "baseline_id": stable_baseline_uuid(facility_id),
            "facility_id": facility_id,
            "baseline_frp": baseline["baseline_frp"],
            "frp_std": baseline["frp_std"],
            "typical_active_hours": json.dumps(
                baseline["typical_active_hours"]
            ),
            "typical_duration": baseline["typical_duration"],
            "seasonal_pattern": json.dumps(baseline["seasonal_pattern"]),
            "historical_event_count": baseline["historical_event_count"],
        }
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
                    CAST(:baseline_id AS uuid),
                    CAST(:facility_id AS uuid),
                    :baseline_frp,
                    :frp_std,
                    CAST(:typical_active_hours AS jsonb),
                    :typical_duration,
                    CAST(:seasonal_pattern AS jsonb),
                    :historical_event_count,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (facility_id)
                DO UPDATE SET
                    baseline_frp = EXCLUDED.baseline_frp,
                    frp_std = EXCLUDED.frp_std,
                    typical_active_hours = EXCLUDED.typical_active_hours,
                    typical_duration = EXCLUDED.typical_duration,
                    seasonal_pattern = EXCLUDED.seasonal_pattern,
                    historical_event_count = EXCLUDED.historical_event_count,
                    updated_at = NOW()
                """
            ),
            payload,
        )

    db.commit()
    return {
        "facilities_processed": len(grouped),
        "events_used": sum(len(events) for events in grouped.values()),
    }


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def _safe_deviation(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return round(value - baseline, 6)


def classify_event(
    event: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify one event against its own facility's behavioral profile."""
    if (
        baseline is None
        or baseline.get("historical_event_count", 0) < MIN_BASELINE_EVENTS
        or baseline.get("baseline_frp") is None
    ):
        return {
            "anomaly_state": "UNKNOWN",
            "baseline_deviation": None,
            "signals": {},
            "decision_basis": "NO_BASELINE",
        }

    observed_frp = _number(event.get("current_frp"))
    if observed_frp is None:
        observed_frp = _number(event.get("mean_frp"))
    baseline_frp = _number(baseline.get("baseline_frp"))
    frp_std = _number(baseline.get("frp_std"))
    frp_deviation = None
    if observed_frp is not None and baseline_frp is not None:
        if frp_std is not None and frp_std > 1e-6:
            frp_deviation = round((observed_frp - baseline_frp) / frp_std, 6)
        else:
            frp_deviation = 0.0 if math.isclose(observed_frp, baseline_frp) else None

    duration = _number(event.get("duration"))
    typical_duration = _number(baseline.get("typical_duration"))
    duration_deviation = None
    if duration is not None and typical_duration is not None:
        duration_deviation = round(
            (duration - typical_duration) / max(abs(typical_duration), 1.0),
            6,
        )

    timestamp = _event_timestamp(event)
    hour_probability = None
    if timestamp is not None:
        hour_probability = _number(
            (baseline.get("typical_active_hours") or {}).get(str(timestamp.hour))
        ) or 0.0

    seasonal_entry = None
    if timestamp is not None:
        seasonal_entry = (baseline.get("seasonal_pattern") or {}).get(
            str(timestamp.month)
        )
    seasonal_frp_deviation = None
    seasonal_event_count = None
    if isinstance(seasonal_entry, dict):
        seasonal_event_count = int(seasonal_entry.get("event_count", 0))
        monthly_frp = _number(seasonal_entry.get("average_frp"))
        if monthly_frp is not None and baseline_frp is not None:
            seasonal_frp_deviation = _safe_deviation(observed_frp, monthly_frp)

    distance = _number(event.get("facility_distance_m"))
    proximity_weight = (
        round(max(0.0, 1.0 - distance / FAR_EVENT_DISTANCE_M), 6)
        if distance is not None
        else None
    )

    built_up = _number(event.get("built_up_fraction")) or 0.0
    forest = _number(event.get("forest_fraction")) or 0.0
    cropland = _number(event.get("cropland_fraction")) or 0.0
    landcover_context = round(built_up - forest - 0.5 * cropland, 6)

    signals = {
        "intensity": {
            "value": observed_frp,
            "baseline": baseline_frp,
            "deviation": frp_deviation,
            "strong": frp_deviation is not None
            and abs(frp_deviation) >= FRP_STRONG_DEVIATION,
            "supporting": frp_deviation is not None
            and abs(frp_deviation) >= FRP_SUPPORTING_DEVIATION,
        },
        "duration": {
            "value": duration,
            "baseline": typical_duration,
            "deviation": duration_deviation,
            "supporting": duration_deviation is not None
            and abs(duration_deviation) >= SIGNAL_DEVIATION,
        },
        "timing": {
            "value": timestamp.hour if timestamp is not None else None,
            "baseline": hour_probability,
            "deviation": (
                round(1.0 - hour_probability, 6)
                if hour_probability is not None
                else None
            ),
            "supporting": hour_probability is not None
            and hour_probability < TIMING_RARITY,
        },
        "seasonal": {
            "value": observed_frp,
            "baseline": (
                seasonal_entry.get("average_frp")
                if isinstance(seasonal_entry, dict)
                else None
            ),
            "deviation": seasonal_frp_deviation,
            "event_count": seasonal_event_count,
            "supporting": seasonal_event_count is not None
            and seasonal_event_count >= 2
            and seasonal_frp_deviation is not None
            and abs(seasonal_frp_deviation) >= FRP_SUPPORTING_DEVIATION,
        },
        "proximity": {
            "value": distance,
            "baseline": FAR_EVENT_DISTANCE_M,
            "deviation": proximity_weight,
            "weight": proximity_weight,
            "supporting": distance is not None and distance > FAR_EVENT_DISTANCE_M,
        },
        "land_cover": {
            "value": {
                "built_up_fraction": built_up,
                "forest_fraction": forest,
                "cropland_fraction": cropland,
            },
            "baseline": "facility-associated context",
            "deviation": landcover_context,
            "supporting": abs(landcover_context) >= 0.5,
        },
    }

    supporting_signals = sum(
        bool(signal.get("supporting"))
        for signal in signals.values()
    )
    strong_intensity = bool(signals["intensity"].get("strong"))
    weighted_support = supporting_signals
    if proximity_weight is not None:
        weighted_support *= max(proximity_weight, 0.25)

    if frp_deviation is None and observed_frp is None:
        anomaly_state = "UNKNOWN"
    elif strong_intensity or weighted_support >= 2:
        anomaly_state = "ANOMALOUS"
    elif baseline.get("historical_event_count", 0) >= PERSISTENT_HISTORY_EVENTS:
        anomaly_state = "PERSISTENT"
    else:
        anomaly_state = "ROUTINE"

    return {
        "anomaly_state": anomaly_state,
        "baseline_deviation": frp_deviation,
        "signals": signals,
        "event_context": {
            "first_seen": event.get("first_seen").isoformat()
            if isinstance(event.get("first_seen"), datetime)
            else None,
            "duration": duration,
            "facility_distance_m": distance,
        },
        "decision_basis": (
            "STRONG_INTENSITY"
            if strong_intensity
            else "MULTI_SIGNAL"
            if weighted_support >= 2
            else "CONSISTENT_HISTORY"
        ),
    }


def _format_number(value: Any, digits: int = 2) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "unknown"


def build_classification_reasons(
    classification: dict[str, Any],
) -> dict[str, Any]:
    """Turn contributing classifier signals into grounded explanations."""
    state = classification["anomaly_state"]
    signals = classification.get("signals", {})
    event_context = classification.get("event_context", {})
    if not isinstance(event_context, dict):
        event_context = {}
    decision_basis = classification.get("decision_basis")
    reasons: list[dict[str, Any]] = []

    intensity = signals.get("intensity", {})
    intensity_deviation = intensity.get("deviation")
    include_intensity = intensity.get("strong") or (
        decision_basis == "MULTI_SIGNAL" and intensity.get("supporting")
    )
    if include_intensity:
        direction = "above" if (intensity_deviation or 0) >= 0 else "below"
        reasons.append(
            {
                "factor": "FRP_DEVIATION",
                "message": (
                    f"Observed FRP is {_format_number(abs(intensity_deviation))} "
                    f"standard deviations {direction} this facility's baseline."
                ),
                "event_value": intensity.get("value"),
                "baseline_value": intensity.get("baseline"),
                "deviation": intensity_deviation,
            }
        )

    duration = signals.get("duration", {})
    if decision_basis == "MULTI_SIGNAL" and duration.get("supporting"):
        direction = "longer" if (duration.get("deviation") or 0) >= 0 else "shorter"
        reasons.append(
            {
                "factor": "DURATION_DEVIATION",
                "message": (
                    f"Event duration is {_format_number(abs(duration.get('deviation')))} "
                    f"relative units {direction} than this facility's typical duration."
                ),
                "event_value": duration.get("value"),
                "baseline_value": duration.get("baseline"),
                "deviation": duration.get("deviation"),
            }
        )

    timing = signals.get("timing", {})
    if decision_basis == "MULTI_SIGNAL" and timing.get("supporting"):
        reasons.append(
            {
                "factor": "TIMING_DEVIATION",
                "message": (
                    f"Event started at hour {timing.get('value')}, which represents "
                    f"only {_format_number((timing.get('baseline') or 0) * 100, 1)}% "
                    "of this facility's historical activity."
                ),
                "event_value": timing.get("value"),
                "baseline_value": timing.get("baseline"),
                "deviation": timing.get("deviation"),
            }
        )

    seasonal = signals.get("seasonal", {})
    if decision_basis == "MULTI_SIGNAL" and seasonal.get("supporting"):
        direction = "above" if (seasonal.get("deviation") or 0) >= 0 else "below"
        reasons.append(
            {
                "factor": "SEASONAL_DEVIATION",
                "message": (
                    f"Observed FRP is {_format_number(abs(seasonal.get('deviation')))} "
                    f"FRP units {direction} the facility's monthly pattern, based on "
                    f"{seasonal.get('event_count')} historical events in that month."
                ),
                "event_value": seasonal.get("value"),
                "baseline_value": seasonal.get("baseline"),
                "deviation": seasonal.get("deviation"),
            }
        )

    proximity = signals.get("proximity", {})
    if decision_basis == "MULTI_SIGNAL" and proximity.get("supporting"):
        reasons.append(
            {
                "factor": "FACILITY_PROXIMITY",
                "message": (
                    f"Event is {_format_number(proximity.get('value'), 0)} m from the "
                    "facility centroid, so facility evidence is weighted down."
                ),
                "event_value": proximity.get("value"),
                "baseline_value": proximity.get("baseline"),
                "deviation": proximity.get("deviation"),
            }
        )

    land_cover = signals.get("land_cover", {})
    if decision_basis == "MULTI_SIGNAL" and land_cover.get("supporting"):
        values = land_cover.get("value", {})
        landcover_label = (
            "industrial"
            if (land_cover.get("deviation") or 0) > 0
            else "non-industrial"
        )
        reasons.append(
            {
                "factor": "LAND_COVER_CONTEXT",
                "message": (
                    f"Land cover is {landcover_label}-leaning: {_format_number(values.get('built_up_fraction', 0) * 100, 1)}% "
                    f"built-up, {_format_number(values.get('forest_fraction', 0) * 100, 1)}% forest, "
                    f"and {_format_number(values.get('cropland_fraction', 0) * 100, 1)}% cropland."
                ),
                "event_value": values,
                "baseline_value": land_cover.get("baseline"),
                "deviation": land_cover.get("deviation"),
            }
        )

    intensity_value = signals.get("intensity", {}).get("value")
    intensity_baseline = signals.get("intensity", {}).get("baseline")
    frp_detail = (
        f"observed FRP {_format_number(intensity_value)} versus a facility median of "
        f"{_format_number(intensity_baseline)}"
        if intensity_value is not None and intensity_baseline is not None
        else "FRP was unavailable"
    )
    event_date = event_context.get("first_seen")
    event_date = event_date[:10] if isinstance(event_date, str) else "an undated observation"

    if state == "ANOMALOUS":
        explanation = (
            f"The {event_date} event is ANOMALOUS: {frp_detail}, with "
            f"{len(reasons)} contributing signal{'s' if len(reasons) != 1 else ''}."
        )
    elif state == "PERSISTENT":
        explanation = (
            f"The {event_date} event is PERSISTENT: {frp_detail} remains consistent "
            "with this facility's established pattern."
        )
    elif state == "ROUTINE":
        explanation = (
            f"The {event_date} event is ROUTINE: {frp_detail} falls within this "
            "facility's observed range."
        )
    else:
        explanation = "No usable facility baseline was available for comparison."

    return {
        "explanation": explanation,
        "reasons": reasons,
        "signals": signals,
        "event_context": event_context,
    }


def classify_events(db: Session) -> dict[str, int]:
    """Classify every thermal event and persist its state and signal values."""
    baseline_rows = db.execute(
        text(
            """
            SELECT
                facility_id::text AS facility_id,
                baseline_frp,
                frp_std,
                typical_active_hours,
                typical_duration,
                seasonal_pattern,
                historical_event_count
            FROM site_baselines
            """
        )
    ).mappings().all()
    baselines = {row["facility_id"]: dict(row) for row in baseline_rows}

    events = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                facility_id::text AS facility_id,
                first_seen,
                current_frp,
                mean_frp,
                duration,
                facility_distance_m,
                built_up_fraction,
                forest_fraction,
                cropland_fraction
            FROM thermal_events
            """
        )
    ).mappings().all()

    counts = Counter()
    payload: list[dict[str, Any]] = []
    for row in events:
        event = dict(row)
        result = classify_event(event, baselines.get(event.get("facility_id")))
        reason_payload = build_classification_reasons(result)
        payload.append(
            {
                "event_id": event["event_id"],
                "baseline_frp": (
                    baselines[event["facility_id"]].get("baseline_frp")
                    if event.get("facility_id") in baselines
                    else None
                ),
                "baseline_deviation": result["baseline_deviation"],
                "anomaly_state": result["anomaly_state"],
                "reasons": json.dumps(reason_payload),
            }
        )
        counts[result["anomaly_state"]] += 1

    if payload:
        db.execute(
            text(
                """
                UPDATE thermal_events AS e
                SET
                    baseline_frp = x.baseline_frp,
                    baseline_deviation = x.baseline_deviation,
                    anomaly_state = x.anomaly_state,
                    classification_reasons = CAST(x.reasons AS jsonb),
                    updated_at = NOW()
                FROM jsonb_to_recordset(CAST(:payload AS jsonb)) AS x(
                    event_id uuid,
                    baseline_frp double precision,
                    baseline_deviation double precision,
                    anomaly_state text,
                    reasons text
                )
                WHERE e.event_id = x.event_id
                """
            ),
            {"payload": json.dumps(payload)},
        )

    db.commit()
    return dict(counts)


def get_facility_event_map(
    db: Session,
    facility_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any] | None:
    """Return facility-centered event geometry with server-side date filtering."""
    facility = db.execute(
        text(
            """
            SELECT facility_id::text AS facility_id, name, latitude, longitude
            FROM facilities
            WHERE facility_id = CAST(:facility_id AS uuid)
            """
        ),
        {"facility_id": facility_id},
    ).mappings().one_or_none()
    if facility is None:
        return None

    conditions = ["facility_id = CAST(:facility_id AS uuid)"]
    params: dict[str, Any] = {"facility_id": facility_id}
    if start_date is not None:
        conditions.append("first_seen >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        conditions.append("first_seen < :end_date")
        params["end_date"] = end_date

    rows = db.execute(
        text(
            f"""
            SELECT
                event_id::text AS event_id,
                latitude,
                longitude,
                first_seen,
                anomaly_state,
                classification,
                current_frp,
                mean_frp,
                facility_distance_m,
                ST_AsGeoJSON(geometry)::json AS geometry,
                CASE
                    WHEN spread_geometry IS NOT NULL
                    THEN ST_AsGeoJSON(spread_geometry)::json
                    ELSE NULL
                END AS spread_geometry
            FROM thermal_events
            WHERE {' AND '.join(conditions)}
            ORDER BY first_seen ASC
            """
        ),
        params,
    ).mappings().all()

    events = [
        {
            "event_id": row["event_id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "first_seen": row["first_seen"].isoformat()
            if row["first_seen"] is not None
            else None,
            "anomaly_state": row["anomaly_state"] or "UNKNOWN",
            "classification": row["classification"],
            "current_frp": row["current_frp"],
            "mean_frp": row["mean_frp"],
            "facility_distance_m": row["facility_distance_m"],
            "geometry": row["geometry"]
            or {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]],
            },
            "spread_geometry": row["spread_geometry"],
        }
        for row in rows
    ]
    usable_events = [
        event
        for event in events
        if event["latitude"] is not None and event["longitude"] is not None
    ]
    if not events:
        state = "NO_EVENTS"
    elif not usable_events:
        state = "NO_GEOLOCATED_EVENTS"
    else:
        state = "READY"

    return {
        "facility": {
            "facility_id": facility["facility_id"],
            "name": facility["name"],
            "latitude": facility["latitude"],
            "longitude": facility["longitude"],
        },
        "state": state,
        "count": len(usable_events),
        "events": usable_events,
    }


def get_facility_environment(
    db: Session,
    facility_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any] | None:
    """Compute facility emissions trend and historical-relative status.

    start_date/end_date restrict which events' emissions are counted, so this
    can be called with the same range as get_facility_event_map to keep the
    emissions view in sync with whatever period the map is currently showing.
    """
    exists = db.execute(
        text("SELECT name FROM facilities WHERE facility_id = CAST(:facility_id AS uuid)"),
        {"facility_id": facility_id},
    ).mappings().one_or_none()
    if exists is None:
        return None

    conditions = [
        "facility_id = CAST(:facility_id AS uuid)",
        "emissions_estimate IS NOT NULL",
    ]
    params: dict[str, Any] = {"facility_id": facility_id}
    if start_date is not None:
        conditions.append("first_seen >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        conditions.append("first_seen < :end_date")
        params["end_date"] = end_date

    is_filtered = start_date is not None or end_date is not None
    period_phrase = "in the selected period" if is_filtered else "on record"

    rows = db.execute(
        text(
            f"""
            SELECT event_id::text AS event_id, first_seen, emissions_estimate
            FROM thermal_events
            WHERE {' AND '.join(conditions)}
            ORDER BY first_seen ASC
            """
        ),
        params,
    ).mappings().all()
    if not rows:
        return {
            "state": "NO_EMISSIONS_DATA",
            "facility_name": exists["name"],
            "trend": "INSUFFICIENT_DATA",
            "total_emissions": None,
            "series": [],
            "contributions": [],
            "statement": (
                f"No event-level emissions estimates are available for this "
                f"facility {period_phrase}."
            ),
        }

    values = [float(row["emissions_estimate"]) for row in rows]
    midpoint = len(values) // 2
    first_half = values[:midpoint] or values
    second_half = values[midpoint:] or values
    first_avg = statistics.mean(first_half)
    second_avg = statistics.mean(second_half)
    change = ((second_avg - first_avg) / first_avg * 100) if first_avg else None
    if len(values) < 4 or change is None:
        trend = "INSUFFICIENT_DATA"
    elif change > 10:
        trend = "INCREASING"
    elif change < -10:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    state = "NORMAL"
    if trend == "INCREASING" and len(values) >= 6:
        state = "WATCH"
    if trend == "INCREASING" and len(values) >= 12:
        state = "EXCEEDANCE"
    change_text = "no comparable trend" if change is None else f"a {change:.1f}% change"
    return {
        "state": state,
        "facility_name": exists["name"],
        "trend": trend,
        "trend_change_percent": round(change, 2) if change is not None else None,
        "total_emissions": round(sum(values), 6),
        "series": [
            {
                "event_id": row["event_id"],
                "date": row["first_seen"].isoformat(),
                "emissions": float(row["emissions_estimate"]),
            }
            for row in rows
        ],
        "contributions": [
            {
                "event_id": row["event_id"],
                "date": row["first_seen"].isoformat(),
                "emissions": float(row["emissions_estimate"]),
            }
            for row in sorted(rows, key=lambda item: item["emissions_estimate"], reverse=True)
        ],
        "statement": (
            f"Relative to this facility's historical emissions pattern, activity "
            f"{period_phrase} is {state.lower()} with {change_text}. This is not a "
            "regulatory determination."
        ),
    }


CONCERN_MIN_EVENTS = 3
CONCERN_RECENT_WINDOW = 6
CONCERN_WEIGHTS = {
    "anomaly_frequency": 0.35,
    "recent_severity": 0.25,
    "overall_risk": 0.25,
    "emissions_trend": 0.15,
}
CONCERN_CUTOFFS = [
    (75, "CRITICAL"),
    (50, "HIGH"),
    (25, "MODERATE"),
    (0, "LOW"),
]


def _concern_level(score: float) -> str:
    for cutoff, label in CONCERN_CUTOFFS:
        if score >= cutoff:
            return label
    return "LOW"


def calculate_concern_score(
    *,
    total_events: int,
    anomalous_events: int,
    avg_risk_score: float | None,
    recent_avg_risk_score: float | None,
    emissions_trend: str | None,
    emissions_trend_change_percent: float | None,
) -> dict[str, Any]:
    """
    Combine anomaly frequency, recent severity, overall risk, and emissions
    trend into a single 0-100 Facility Concern Score using an explicit
    weighted sum (see CONCERN_WEIGHTS). Prototype-level indicator, not a
    validated risk model - internal Phoenix indicator, not an official
    environmental ranking.
    """
    if total_events < CONCERN_MIN_EVENTS or avg_risk_score is None:
        return {
            "state": "INSUFFICIENT_DATA",
            "score": None,
            "level": None,
            "components": {},
            "weights": CONCERN_WEIGHTS,
            "statement": (
                f"Fewer than {CONCERN_MIN_EVENTS} classified events with risk "
                "scores are available - not enough history for a reliable "
                "concern indicator."
            ),
        }

    anomaly_frequency_pct = (anomalous_events / total_events) * 100
    recent_severity = (
        recent_avg_risk_score if recent_avg_risk_score is not None else avg_risk_score
    )
    overall_risk = avg_risk_score

    emissions_component = 0.0
    if emissions_trend == "INCREASING":
        emissions_component = min(100.0, abs(emissions_trend_change_percent or 25.0))
    elif emissions_trend == "DECREASING":
        emissions_component = max(
            0.0, 25.0 - min(25.0, abs(emissions_trend_change_percent or 0.0))
        )
    elif emissions_trend == "STABLE":
        emissions_component = 15.0
    # INSUFFICIENT_DATA / no emissions trend -> stays at 0; a facility isn't
    # penalized just because emissions data doesn't exist yet.

    components = {
        "anomaly_frequency": round(min(100.0, anomaly_frequency_pct), 2),
        "recent_severity": round(min(100.0, recent_severity), 2),
        "overall_risk": round(min(100.0, overall_risk), 2),
        "emissions_trend": round(emissions_component, 2),
    }

    score = round(
        sum(components[key] * weight for key, weight in CONCERN_WEIGHTS.items()),
        2,
    )
    level = _concern_level(score)

    statement = (
        f"Facility Concern Score of {score:.0f}/100 ({level.title()} Concern), "
        f"based on {anomalous_events} of {total_events} historical events "
        f"classified anomalous, an average risk score of {overall_risk:.0f}, "
        f"and an emissions trend that is {(emissions_trend or 'unavailable').lower()}. "
        "This is an internal Phoenix indicator, not an official environmental ranking."
    )

    return {
        "state": "READY",
        "score": score,
        "level": level,
        "components": components,
        "weights": CONCERN_WEIGHTS,
        "statement": statement,
    }


def get_facility_concern(db: Session, facility_id: str) -> dict[str, Any] | None:
    """Compute the Facility Concern Score for a single facility."""
    facility = db.execute(
        text("SELECT name FROM facilities WHERE facility_id = CAST(:facility_id AS uuid)"),
        {"facility_id": facility_id},
    ).mappings().one_or_none()
    if facility is None:
        return None

    stats = db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE anomaly_state IS NOT NULL) AS total_events,
                COUNT(*) FILTER (WHERE anomaly_state = 'ANOMALOUS') AS anomalous_events,
                AVG(risk_score) AS avg_risk_score
            FROM thermal_events
            WHERE facility_id = CAST(:facility_id AS uuid)
            """
        ),
        {"facility_id": facility_id},
    ).mappings().one()

    recent = db.execute(
        text(
            """
            SELECT AVG(risk_score) AS recent_avg_risk_score
            FROM (
                SELECT risk_score
                FROM thermal_events
                WHERE facility_id = CAST(:facility_id AS uuid)
                  AND risk_score IS NOT NULL
                ORDER BY first_seen DESC
                LIMIT :window
            ) recent_events
            """
        ),
        {"facility_id": facility_id, "window": CONCERN_RECENT_WINDOW},
    ).mappings().one()

    environment = get_facility_environment(db, facility_id)

    result = calculate_concern_score(
        total_events=int(stats["total_events"] or 0),
        anomalous_events=int(stats["anomalous_events"] or 0),
        avg_risk_score=(
            float(stats["avg_risk_score"]) if stats["avg_risk_score"] is not None else None
        ),
        recent_avg_risk_score=(
            float(recent["recent_avg_risk_score"])
            if recent["recent_avg_risk_score"] is not None
            else None
        ),
        emissions_trend=environment.get("trend") if environment else None,
        emissions_trend_change_percent=(
            environment.get("trend_change_percent") if environment else None
        ),
    )
    result["facility_id"] = facility_id
    result["facility_name"] = facility["name"]
    return result


def get_all_facility_environments(db: Session) -> dict[str, dict[str, Any]]:
    """
    Batch version of get_facility_environment's trend calculation - one query
    for every facility instead of one query PER facility. Used only by
    get_all_facility_concerns (the /facilities list); the single-facility
    get_facility_environment endpoint is unaffected and still does its own
    fuller computation (series, contributions, statement) for the detail page.
    """
    rows = db.execute(
        text(
            """
            SELECT
                facility_id::text AS facility_id,
                first_seen,
                emissions_estimate
            FROM thermal_events
            WHERE facility_id IS NOT NULL
              AND emissions_estimate IS NOT NULL
            ORDER BY facility_id, first_seen ASC
            """
        )
    ).mappings().all()

    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["facility_id"]].append(float(row["emissions_estimate"]))

    results: dict[str, dict[str, Any]] = {}
    for facility_id, values in grouped.items():
        midpoint = len(values) // 2
        first_half = values[:midpoint] or values
        second_half = values[midpoint:] or values
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        change = ((second_avg - first_avg) / first_avg * 100) if first_avg else None

        if len(values) < 4 or change is None:
            trend = "INSUFFICIENT_DATA"
        elif change > 10:
            trend = "INCREASING"
        elif change < -10:
            trend = "DECREASING"
        else:
            trend = "STABLE"

        results[facility_id] = {
            "trend": trend,
            "trend_change_percent": round(change, 2) if change is not None else None,
        }

    return results


def get_all_facility_concerns(db: Session) -> dict[str, dict[str, Any]]:
    """
    Bulk-compute concern scores for every facility, for the /facilities list
    endpoint. Uses one batch environment query (get_all_facility_environments)
    instead of calling get_facility_environment per facility - avoids the
    N+1 query pattern that scaled badly as facility count grew and was the
    cause of the slow /facilities load.
    """
    stats_rows = db.execute(
        text(
            """
            SELECT
                facility_id::text AS facility_id,
                COUNT(*) FILTER (WHERE anomaly_state IS NOT NULL) AS total_events,
                COUNT(*) FILTER (WHERE anomaly_state = 'ANOMALOUS') AS anomalous_events,
                AVG(risk_score) AS avg_risk_score
            FROM thermal_events
            WHERE facility_id IS NOT NULL
            GROUP BY facility_id
            """
        )
    ).mappings().all()

    recent_rows = db.execute(
        text(
            """
            SELECT facility_id::text AS facility_id, AVG(risk_score) AS recent_avg_risk_score
            FROM (
                SELECT
                    facility_id,
                    risk_score,
                    ROW_NUMBER() OVER (
                        PARTITION BY facility_id ORDER BY first_seen DESC
                    ) AS rn
                FROM thermal_events
                WHERE facility_id IS NOT NULL AND risk_score IS NOT NULL
            ) ranked
            WHERE rn <= :window
            GROUP BY facility_id
            """
        ),
        {"window": CONCERN_RECENT_WINDOW},
    ).mappings().all()
    recent_by_facility = {row["facility_id"]: row["recent_avg_risk_score"] for row in recent_rows}

    environments = get_all_facility_environments(db)

    results: dict[str, dict[str, Any]] = {}
    for row in stats_rows:
        facility_id = row["facility_id"]
        environment = environments.get(facility_id, {})
        recent_avg = recent_by_facility.get(facility_id)
        results[facility_id] = calculate_concern_score(
            total_events=int(row["total_events"] or 0),
            anomalous_events=int(row["anomalous_events"] or 0),
            avg_risk_score=(
                float(row["avg_risk_score"]) if row["avg_risk_score"] is not None else None
            ),
            recent_avg_risk_score=float(recent_avg) if recent_avg is not None else None,
            emissions_trend=environment.get("trend"),
            emissions_trend_change_percent=environment.get("trend_change_percent"),
        )
    return results