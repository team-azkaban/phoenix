from __future__ import annotations

import hashlib
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from db.database import SessionLocal


# ============================================================
# INPUT FILES
# ============================================================

OBS_FILE = (
    ROOT /
    "data/firms/dahej/dahej_firms_observations.csv"
)

EVENT_FILE = (
    ROOT /
    "data/firms/dahej/dahej_candidate_events.csv"
)

MAPPING_FILE = (
    ROOT /
    "data/firms/dahej/dahej_event_observations.csv"
)

FACILITY_FILE = (
    ROOT /
    "data/facilities/dahej/dahej_facilities.csv"
)


BATCH_SIZE = 500


# ============================================================
# HELPERS
# ============================================================

def require_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found:\n{path}"
        )


def clean(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    return value if value else None


def number(value):
    if pd.isna(value):
        return None

    return float(value)


def integer(value):
    if pd.isna(value):
        return None

    return int(value)


def timestamp(value):
    if pd.isna(value):
        return None

    result = pd.to_datetime(
        value,
        utc=True,
        errors="coerce"
    )

    if pd.isna(result):
        return None

    return result.to_pydatetime()


def stable_uuid(identifier: str) -> str:
    """
    Convert a human-readable Phoenix identifier into
    a deterministic UUID.

    Example:

        EVT-DAHEJ-02505
            ↓
        deterministic UUID

    Same input always produces the same UUID.
    """

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"phoenix-dahej:{identifier}"
        )
    )


# ============================================================
# LOAD OBSERVATIONS
# ============================================================

def load_observations(db, df):

    print()
    print("=" * 70)
    print("THERMAL OBSERVATIONS")
    print("=" * 70)

    required = [
        "observation_id",
        "timestamp",
        "latitude",
        "longitude",
        "source",
    ]

    missing = [
        x for x in required
        if x not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Observation CSV missing: {missing}"
        )

    sql = text(
        """
        INSERT INTO thermal_observations
        (
            observation_id,
            timestamp,
            latitude,
            longitude,
            sensor,
            satellite,
            frp,
            brightness_temperature,
            confidence,
            day_night,
            source,
            source_record_id,
            geometry,
            ingestion_timestamp,
            data_version
        )
        VALUES
        (
            CAST(:observation_id AS uuid),
            :timestamp,
            :latitude,
            :longitude,
            :sensor,
            :satellite,
            :frp,
            :brightness_temperature,
            :confidence,
            :day_night,
            :source,
            :source_record_id,

            CASE
                WHEN :latitude IS NOT NULL
                 AND :longitude IS NOT NULL
                THEN
                    ST_SetSRID(
                        ST_MakePoint(
                            :longitude,
                            :latitude
                        ),
                        4326
                    )::geography
                ELSE NULL
            END,

            :ingestion_timestamp,
            :data_version
        )

        ON CONFLICT (observation_id)
        DO NOTHING
        """
    )

    records = []

    for _, row in df.iterrows():

        source_id = clean(
            row["observation_id"]
        )

        records.append(
            {
                "observation_id":
                    stable_uuid(source_id),

                "timestamp":
                    timestamp(
                        row["timestamp"]
                    ),

                "latitude":
                    number(
                        row["latitude"]
                    ),

                "longitude":
                    number(
                        row["longitude"]
                    ),

                "sensor":
                    clean(
                        row.get(
                            "firms_sensor"
                        )
                    ),

                "satellite":
                    clean(
                        row.get(
                            "satellite"
                        )
                    ),

                "frp":
                    number(
                        row.get("frp")
                    ),

                "brightness_temperature":
                    number(
                        row.get("bright_ti4")
                    ),

                "confidence":
                    number(
                        row.get(
                            "confidence_score"
                        )
                    ),

                "day_night":
                    clean(
                        row.get("daynight")
                    ),

                "source":
                    clean(
                        row["source"]
                    ),

                "source_record_id":
                    clean(
                        row.get(
                            "source_record_id"
                        )
                    ),

                "ingestion_timestamp":
                    datetime.now(
                        timezone.utc
                    ),

                "data_version":
                    clean(
                        row.get("version")
                    ),
            }
        )

    for i in range(
        0,
        len(records),
        BATCH_SIZE
    ):

        db.execute(
            sql,
            records[
                i:i + BATCH_SIZE
            ]
        )

    print(
        f"CSV observations : {len(df):,}"
    )

    print(
        "Database observations loaded."
    )


# ============================================================
# LOAD FACILITIES
# ============================================================

def load_facilities(db, df):

    print()
    print("=" * 70)
    print("FACILITIES")
    print("=" * 70)

    sql = text(
        """
        INSERT INTO facilities
        (
            facility_id,
            name,
            operator,
            facility_type,
            latitude,
            longitude,
            geometry,
            source
        )
        VALUES
        (
            CAST(:facility_id AS uuid),
            :name,
            :operator,
            :facility_type,
            :latitude,
            :longitude,

            CASE
                WHEN :latitude IS NOT NULL
                 AND :longitude IS NOT NULL
                THEN
                    ST_SetSRID(
                        ST_MakePoint(
                            :longitude,
                            :latitude
                        ),
                        4326
                    )::geography
                ELSE NULL
            END,

            :source
        )

        ON CONFLICT (facility_id)
        DO UPDATE SET

            name =
                EXCLUDED.name,

            operator =
                EXCLUDED.operator,

            facility_type =
                EXCLUDED.facility_type,

            latitude =
                EXCLUDED.latitude,

            longitude =
                EXCLUDED.longitude,

            geometry =
                EXCLUDED.geometry,

            source =
                EXCLUDED.source,

            updated_at =
                NOW()
        """
    )

    records = []

    for _, row in df.iterrows():

        records.append(
            {
                "facility_id":
                    stable_uuid(
                        clean(
                            row["facility_id"]
                        )
                    ),

                "name":
                    clean(
                        row["name"]
                    ),

                "operator":
                    clean(
                        row["operator"]
                    ),

                "facility_type":
                    clean(
                        row["facility_type"]
                    ),

                "latitude":
                    number(
                        row["latitude"]
                    ),

                "longitude":
                    number(
                        row["longitude"]
                    ),

                "source":
                    clean(
                        row["source"]
                    ),
            }
        )

    db.execute(
        sql,
        records
    )

    print(
        f"Facilities loaded: {len(records):,}"
    )


# ============================================================
# LOAD EVENTS
# ============================================================

def load_events(db, df):

    print()
    print("=" * 70)
    print("THERMAL EVENTS")
    print("=" * 70)

    required = [
        "event_id",
        "first_seen",
        "last_seen",
        "latitude",
        "longitude",
    ]

    missing = [
        x for x in required
        if x not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Event CSV missing: {missing}"
        )

    sql = text(
        """
        INSERT INTO thermal_events
        (
            event_id,
            first_seen,
            last_seen,
            latitude,
            longitude,
            geometry,
            observation_count,
            current_frp,
            max_frp,
            mean_frp,
            frp_growth,
            duration,
            created_at,
            updated_at
        )
        VALUES
        (
            CAST(:event_id AS uuid),
            :first_seen,
            :last_seen,
            :latitude,
            :longitude,

            CASE
                WHEN :latitude IS NOT NULL
                 AND :longitude IS NOT NULL
                THEN
                    ST_SetSRID(
                        ST_MakePoint(
                            :longitude,
                            :latitude
                        ),
                        4326
                    )::geography
                ELSE NULL
            END,

            :observation_count,
            :current_frp,
            :max_frp,
            :mean_frp,
            :frp_growth,
            :duration,
            NOW(),
            NOW()
        )

        ON CONFLICT (event_id)
        DO UPDATE SET

            first_seen =
                EXCLUDED.first_seen,

            last_seen =
                EXCLUDED.last_seen,

            latitude =
                EXCLUDED.latitude,

            longitude =
                EXCLUDED.longitude,

            geometry =
                EXCLUDED.geometry,

            observation_count =
                EXCLUDED.observation_count,

            current_frp =
                EXCLUDED.current_frp,

            max_frp =
                EXCLUDED.max_frp,

            mean_frp =
                EXCLUDED.mean_frp,

            frp_growth =
                EXCLUDED.frp_growth,

            duration =
                EXCLUDED.duration,

            updated_at =
                NOW()
        """
    )

    records = []

    for _, row in df.iterrows():

        source_event_id = clean(
            row["event_id"]
        )

        records.append(
            {
                "event_id":
                    stable_uuid(
                        source_event_id
                    ),

                "first_seen":
                    timestamp(
                        row["first_seen"]
                    ),

                "last_seen":
                    timestamp(
                        row["last_seen"]
                    ),

                "latitude":
                    number(
                        row["latitude"]
                    ),

                "longitude":
                    number(
                        row["longitude"]
                    ),

                "observation_count":
                    integer(
                        row.get(
                            "observation_count"
                        )
                    ),

                "current_frp":
                    number(
                        row.get(
                            "current_frp"
                        )
                    ),

                "max_frp":
                    number(
                        row.get(
                            "max_frp"
                        )
                    ),

                "mean_frp":
                    number(
                        row.get(
                            "mean_frp"
                        )
                    ),

                "frp_growth":
                    number(
                        row.get(
                            "frp_growth"
                        )
                    ),

                "duration":
                    number(
                        row.get(
                            "duration"
                        )
                    ),
            }
        )

    for i in range(
        0,
        len(records),
        BATCH_SIZE
    ):

        db.execute(
            sql,
            records[
                i:i + BATCH_SIZE
            ]
        )

    print(
        f"Events loaded: {len(records):,}"
    )


# ============================================================
# LOAD EVENT ↔ OBSERVATION
# ============================================================

def load_event_observations(db, df):

    print()
    print("=" * 70)
    print("EVENT ↔ OBSERVATION MAPPING")
    print("=" * 70)

    required = [
        "event_id",
        "observation_id",
    ]

    missing = [
        x for x in required
        if x not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Mapping CSV missing: {missing}"
        )

    sql = text(
        """
        INSERT INTO event_observations
        (
            event_id,
            observation_id
        )
        VALUES
        (
            CAST(:event_id AS uuid),
            CAST(:observation_id AS uuid)
        )

        ON CONFLICT
        (
            event_id,
            observation_id
        )
        DO NOTHING
        """
    )

    records = []

    for _, row in df.iterrows():

        records.append(
            {
                "event_id":
                    stable_uuid(
                        clean(
                            row["event_id"]
                        )
                    ),

                "observation_id":
                    stable_uuid(
                        clean(
                            row["observation_id"]
                        )
                    ),
            }
        )

    for i in range(
        0,
        len(records),
        BATCH_SIZE
    ):

        db.execute(
            sql,
            records[
                i:i + BATCH_SIZE
            ]
        )

    print(
        f"Mappings loaded: {len(records):,}"
    )


# ============================================================
# VALIDATION
# ============================================================

def validate(db):

    print()
    print("=" * 70)
    print("DATABASE VALIDATION")
    print("=" * 70)

    queries = {
        "thermal_observations":
            """
            SELECT COUNT(*)
            FROM thermal_observations
            """,

        "thermal_events":
            """
            SELECT COUNT(*)
            FROM thermal_events
            """,

        "event_observations":
            """
            SELECT COUNT(*)
            FROM event_observations
            """,

        "facilities":
            """
            SELECT COUNT(*)
            FROM facilities
            """,
    }

    counts = {}

    for name, query in queries.items():

        count = db.execute(
            text(query)
        ).scalar_one()

        counts[name] = count

        print(
            f"{name:25} {count:,}"
        )

    # --------------------------------------------------------
    # Orphan mappings
    # --------------------------------------------------------

    orphan_observations = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM event_observations eo

            LEFT JOIN thermal_observations o
                ON o.observation_id =
                   eo.observation_id

            WHERE o.observation_id IS NULL
            """
        )
    ).scalar_one()

    orphan_events = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM event_observations eo

            LEFT JOIN thermal_events e
                ON e.event_id =
                   eo.event_id

            WHERE e.event_id IS NULL
            """
        )
    ).scalar_one()

    events_without_observations = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM thermal_events e

            LEFT JOIN event_observations eo
                ON eo.event_id =
                   e.event_id

            WHERE eo.event_id IS NULL
            """
        )
    ).scalar_one()

    print()
    print(
        f"Orphan observation mappings : "
        f"{orphan_observations:,}"
    )

    print(
        f"Orphan event mappings       : "
        f"{orphan_events:,}"
    )

    print(
        f"Events without observations : "
        f"{events_without_observations:,}"
    )

    if orphan_observations != 0:
        raise RuntimeError(
            "FAIL: orphan observation mappings."
        )

    if orphan_events != 0:
        raise RuntimeError(
            "FAIL: orphan event mappings."
        )

    if events_without_observations != 0:
        raise RuntimeError(
            "FAIL: events without observations."
        )

    print()
    print(
        "DATABASE VALIDATION PASSED"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("PHOENIX — DAHEJ POC → SUPABASE")
    print("=" * 70)

    files = [
        OBS_FILE,
        EVENT_FILE,
        MAPPING_FILE,
        FACILITY_FILE,
    ]

    for file in files:
        require_file(file)

    observations = pd.read_csv(
        OBS_FILE
    )

    events = pd.read_csv(
        EVENT_FILE
    )

    mappings = pd.read_csv(
        MAPPING_FILE
    )

    facilities = pd.read_csv(
        FACILITY_FILE
    )

    print()
    print("INPUT DATA")
    print(
        f"Observations : {len(observations):,}"
    )
    print(
        f"Events       : {len(events):,}"
    )
    print(
        f"Mappings     : {len(mappings):,}"
    )
    print(
        f"Facilities   : {len(facilities):,}"
    )

    # --------------------------------------------------------
    # Verify source IDs are unique
    # --------------------------------------------------------

    if observations["observation_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate observation_id values found."
        )

    if events["event_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate event_id values found."
        )

    if facilities["facility_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate facility_id values found."
        )

    # --------------------------------------------------------
    # Show UUID mapping example
    # --------------------------------------------------------

    print()
    print("UUID MAPPING EXAMPLE")

    print(
        f"Event: EVT-DAHEJ-02505"
    )

    print(
        f"UUID:  {stable_uuid('EVT-DAHEJ-02505')}"
    )

    print()

    print(
        "Human-readable source IDs remain deterministic:"
    )

    print(
        "EVT-DAHEJ-02505 will always map to the same UUID."
    )

    # --------------------------------------------------------
    # DB transaction
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        load_observations(
            db,
            observations
        )

        db.commit()

        load_facilities(
            db,
            facilities
        )

        db.commit()

        load_events(
            db,
            events
        )

        db.commit()

        load_event_observations(
            db,
            mappings
        )

        db.commit()

        validate(db)

        print()
        print("=" * 70)
        print("PHOENIX POC DATABASE LOAD COMPLETE")
        print("=" * 70)

        print()
        print(
            "Supabase now contains the core Dahej POC dataset."
        )

    except Exception:

        db.rollback()

        print()
        print(
            "LOAD FAILED."
        )

        print(
            "Current transaction rolled back."
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()