from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd
from sqlalchemy import text

from db.database import SessionLocal


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MINING_FILE = (
    PROJECT_ROOT
    / "data"
    / "context"
    / "mining"
    / "dahej_mining_context.csv"
)

FLARE_FILE = (
    PROJECT_ROOT
    / "data"
    / "context"
    / "flare"
    / "dahej_flare_context.csv"
)

BATCH_SIZE = 1000


# ============================================================
# DISTANCE
# ============================================================

def haversine_m(lat1, lon1, lat2, lon2):
    earth_radius_m = 6_371_008.8

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return earth_radius_m * (
        2 * atan2(sqrt(a), sqrt(1 - a))
    )


# ============================================================
# CSV
# ============================================================

def load_csv(path, required, label):

    if not path.exists():
        raise FileNotFoundError(
            f"{label} file not found:\n{path}"
        )

    df = pd.read_csv(path)

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{label} missing columns: "
            + ", ".join(missing)
        )

    if df.empty:
        raise ValueError(
            f"{label} CSV is empty."
        )

    return df


# ============================================================
# TABLES
# ============================================================

def create_tables(db):

    print("\n[1/5] Creating context tables...", flush=True)

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS mining_context (
                context_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                context_type TEXT,
                material TEXT,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                lease_area_ha DOUBLE PRECISION,
                context_radius_m DOUBLE PRECISION,
                source TEXT,
                source_type TEXT,
                confidence TEXT,
                is_approximate BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS event_mining_context (
                event_id UUID NOT NULL,
                context_id TEXT NOT NULL,
                distance_m DOUBLE PRECISION NOT NULL,
                within_context_radius BOOLEAN NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),

                PRIMARY KEY (event_id, context_id),

                FOREIGN KEY (event_id)
                    REFERENCES thermal_events(event_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (context_id)
                    REFERENCES mining_context(context_id)
                    ON DELETE CASCADE
            );
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS flare_context (
                context_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                context_type TEXT,
                facility_type TEXT,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                context_radius_m DOUBLE PRECISION,
                source TEXT,
                source_type TEXT,
                confidence TEXT,
                is_approximate BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS event_flare_context (
                event_id UUID NOT NULL,
                context_id TEXT NOT NULL,
                distance_m DOUBLE PRECISION NOT NULL,
                within_context_radius BOOLEAN NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),

                PRIMARY KEY (event_id, context_id),

                FOREIGN KEY (event_id)
                    REFERENCES thermal_events(event_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (context_id)
                    REFERENCES flare_context(context_id)
                    ON DELETE CASCADE
            );
            """
        )
    )

    db.commit()

    print("      Tables ready.", flush=True)


# ============================================================
# LOAD CONTEXT RECORDS
# ============================================================

def load_context_records(db, mining_df, flare_df):

    print("\n[2/5] Loading context records...", flush=True)

    for _, row in mining_df.iterrows():

        db.execute(
            text(
                """
                INSERT INTO mining_context (
                    context_id,
                    name,
                    context_type,
                    material,
                    latitude,
                    longitude,
                    lease_area_ha,
                    context_radius_m,
                    source,
                    source_type,
                    confidence,
                    is_approximate
                )
                VALUES (
                    :context_id,
                    :name,
                    :context_type,
                    :material,
                    :latitude,
                    :longitude,
                    :lease_area_ha,
                    :context_radius_m,
                    :source,
                    :source_type,
                    :confidence,
                    :is_approximate
                )
                ON CONFLICT (context_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    context_type = EXCLUDED.context_type,
                    material = EXCLUDED.material,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    lease_area_ha = EXCLUDED.lease_area_ha,
                    context_radius_m = EXCLUDED.context_radius_m,
                    source = EXCLUDED.source,
                    source_type = EXCLUDED.source_type,
                    confidence = EXCLUDED.confidence,
                    is_approximate = EXCLUDED.is_approximate;
                """
            ),
            {
                "context_id": str(row.context_id),
                "name": str(row["name"]),
                "context_type": str(row["context_type"]),
                "material": str(row["material"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "lease_area_ha": float(row["lease_area_ha"]),
                "context_radius_m": float(row["context_radius_m"]),
                "source": str(row["source"]),
                "source_type": str(row["source_type"]),
                "confidence": str(row["confidence"]),
                "is_approximate": str(
                    row["is_approximate"]
                ).lower() == "true",
            },
        )

    for _, row in flare_df.iterrows():

        db.execute(
            text(
                """
                INSERT INTO flare_context (
                    context_id,
                    name,
                    context_type,
                    facility_type,
                    latitude,
                    longitude,
                    context_radius_m,
                    source,
                    source_type,
                    confidence,
                    is_approximate
                )
                VALUES (
                    :context_id,
                    :name,
                    :context_type,
                    :facility_type,
                    :latitude,
                    :longitude,
                    :context_radius_m,
                    :source,
                    :source_type,
                    :confidence,
                    :is_approximate
                )
                ON CONFLICT (context_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    context_type = EXCLUDED.context_type,
                    facility_type = EXCLUDED.facility_type,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    context_radius_m = EXCLUDED.context_radius_m,
                    source = EXCLUDED.source,
                    source_type = EXCLUDED.source_type,
                    confidence = EXCLUDED.confidence,
                    is_approximate = EXCLUDED.is_approximate;
                """
            ),
            {
                "context_id": str(row.context_id),
                "name": str(row["name"]),
                "context_type": str(row["context_type"]),
                "facility_type": str(row["facility_type"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "context_radius_m": float(row["context_radius_m"]),
                "source": str(row["source"]),
                "source_type": str(row["source_type"]),
                "confidence": str(row["confidence"]),
                "is_approximate": str(
                    row["is_approximate"]
                ).lower() == "true",
            },
        )

    db.commit()

    print(
        f"      Mining contexts: {len(mining_df)}",
        flush=True,
    )

    print(
        f"      Flare contexts:  {len(flare_df)}",
        flush=True,
    )


# ============================================================
# GET EVENTS
# ============================================================

def get_events(db):

    print("\n[3/5] Reading thermal events...", flush=True)

    rows = db.execute(
        text(
            """
            SELECT
                event_id,
                latitude,
                longitude
            FROM thermal_events
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
            ORDER BY event_id;
            """
        )
    ).mappings().all()

    print(
        f"      Events loaded: {len(rows)}",
        flush=True,
    )

    return rows


# ============================================================
# BULK RELATIONSHIP INSERT
# ============================================================

def insert_relationships(
    db,
    events,
    contexts,
    table_name,
    context_id_column,
    radius_column,
    progress_label,
):

    total = len(events) * len(contexts)

    print(
        f"\n{progress_label}",
        flush=True,
    )

    print(
        f"      Total relationships: {total}",
        flush=True,
    )

    insert_sql = text(
        f"""
        INSERT INTO {table_name} (
            event_id,
            {context_id_column},
            distance_m,
            within_context_radius
        )
        VALUES (
            :event_id,
            :context_id,
            :distance_m,
            :within_context_radius
        )
        ON CONFLICT (
            event_id,
            {context_id_column}
        )
        DO UPDATE SET
            distance_m = EXCLUDED.distance_m,
            within_context_radius =
                EXCLUDED.within_context_radius;
        """
    )

    batch = []
    processed = 0
    within_count = 0

    for event in events:

        event_lat = event["latitude"]
        event_lon = event["longitude"]

        for _, context in contexts.iterrows():

            distance_m = haversine_m(
                event_lat,
                event_lon,
                context["latitude"],
                context["longitude"],
            )

            radius_m = float(
                context[radius_column]
            )

            within = distance_m <= radius_m

            if within:
                within_count += 1

            batch.append(
                {
                    "event_id": event["event_id"],
                    "context_id": str(
                        context["context_id"]
                    ),
                    "distance_m": distance_m,
                    "within_context_radius": within,
                }
            )

            if len(batch) >= BATCH_SIZE:

                db.execute(
                    insert_sql,
                    batch,
                )

                db.commit()

                processed += len(batch)

                percent = (
                    processed / total
                ) * 100

                print(
                    f"      Progress: "
                    f"{processed:,}/{total:,} "
                    f"({percent:5.1f}%)",
                    flush=True,
                )

                batch.clear()

    if batch:

        db.execute(
            insert_sql,
            batch,
        )

        db.commit()

        processed += len(batch)

        print(
            f"      Progress: "
            f"{processed:,}/{total:,} "
            f"(100.0%)",
            flush=True,
        )

    print(
        f"      Within radius: {within_count}",
        flush=True,
    )


# ============================================================
# VERIFICATION
# ============================================================

def verify(db):

    print("\n[5/5] Verifying Supabase...", flush=True)

    queries = {
        "mining_context":
            "SELECT COUNT(*) FROM mining_context",

        "event_mining_context":
            "SELECT COUNT(*) FROM event_mining_context",

        "mining within radius":
            """
            SELECT COUNT(*)
            FROM event_mining_context
            WHERE within_context_radius = TRUE
            """,

        "flare_context":
            "SELECT COUNT(*) FROM flare_context",

        "event_flare_context":
            "SELECT COUNT(*) FROM event_flare_context",

        "flare within radius":
            """
            SELECT COUNT(*)
            FROM event_flare_context
            WHERE within_context_radius = TRUE
            """,
    }

    for name, query in queries.items():

        value = db.execute(
            text(query)
        ).scalar()

        print(
            f"      {name:<30} {value}",
            flush=True,
        )

    print("\n      Closest flare events:")

    rows = db.execute(
        text(
            """
            SELECT
                ef.event_id,
                ef.distance_m,
                e.max_frp,
                f.name
            FROM event_flare_context ef
            JOIN thermal_events e
                ON e.event_id = ef.event_id
            JOIN flare_context f
                ON f.context_id = ef.context_id
            ORDER BY ef.distance_m
            LIMIT 10;
            """
        )
    ).mappings().all()

    for row in rows:

        frp = (
            row["max_frp"]
            if row["max_frp"] is not None
            else 0
        )

        print(
            f"      {row['distance_m']:7.1f} m | "
            f"FRP {frp:6.2f} | "
            f"{row['name']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("PHOENIX MINING + FLARE CONTEXT LOADER")
    print("=" * 60)

    mining_required = [
        "context_id",
        "name",
        "context_type",
        "material",
        "latitude",
        "longitude",
        "lease_area_ha",
        "context_radius_m",
        "source",
        "source_type",
        "confidence",
        "is_approximate",
    ]

    flare_required = [
        "context_id",
        "name",
        "context_type",
        "facility_type",
        "latitude",
        "longitude",
        "context_radius_m",
        "source",
        "source_type",
        "confidence",
        "is_approximate",
    ]

    print("\n[0/5] Reading CSV files...", flush=True)

    mining_df = load_csv(
        MINING_FILE,
        mining_required,
        "Mining context",
    )

    flare_df = load_csv(
        FLARE_FILE,
        flare_required,
        "Flare context",
    )

    print(
        f"      Mining records: {len(mining_df)}",
        flush=True,
    )

    print(
        f"      Flare records:  {len(flare_df)}",
        flush=True,
    )

    db = SessionLocal()

    try:

        create_tables(db)

        load_context_records(
            db,
            mining_df,
            flare_df,
        )

        events = get_events(db)

        print(
            "\n[4/5] Building event relationships...",
            flush=True,
        )

        insert_relationships(
            db=db,
            events=events,
            contexts=mining_df,
            table_name="event_mining_context",
            context_id_column="context_id",
            radius_column="context_radius_m",
            progress_label="      Mining relationships",
        )

        insert_relationships(
            db=db,
            events=events,
            contexts=flare_df,
            table_name="event_flare_context",
            context_id_column="context_id",
            radius_column="context_radius_m",
            progress_label="      Flare relationships",
        )

        verify(db)

        print(
            "\n" + "=" * 60,
            flush=True,
        )

        print(
            "LOAD COMPLETE",
            flush=True,
        )

        print(
            "=" * 60,
            flush=True,
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()