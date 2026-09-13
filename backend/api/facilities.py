from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db


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

        ORDER BY name ASC
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

                "historical_event_count": row[
                    "historical_event_count"
                ],

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
            }
        )

    return {
        "count": len(facilities),
        "facilities": facilities,
    }