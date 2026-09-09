from __future__ import annotations

import hashlib
import io
import os
import time
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
import requests


# ============================================================
# PHOENIX - DAHEJ FIRMS DATASET BUILDER
# ============================================================
#
# Purpose:
#   Build a clean, reproducible Dahej FIRMS dataset for the POC.
#
# Important:
#   This script DOES NOT classify fires.
#   It DOES NOT use facility information.
#   It DOES NOT label observations as industrial/non-industrial.
#
# It creates the evidence layer that later supports:
#
#   FIRMS observations
#          ↓
#   Thermal Events
#          ↓
#   spatial/temporal/thermal context
#          ↓
#   facility enrichment
#          ↓
#   classification
#
# NASA FIRMS Area API:
#   https://firms.modaps.eosdis.nasa.gov/api/area/
#
# ============================================================


# ------------------------------------------------------------
# PROJECT PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[3]

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "firms"
    / "dahej"
)

RAW_DIR = OUTPUT_DIR / "raw"


# ------------------------------------------------------------
# FIRMS CONFIGURATION
# ------------------------------------------------------------

FIRMS_API_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
)
load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY environment variable is not set.\n"
        "Set it before running the script."
    )


# Standard Processing products.
#
# We intentionally use these two because they are the
# products already being used for the PHOENIX POC.
SENSORS = [
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]


# ------------------------------------------------------------
# TEMPORAL COVERAGE
# ------------------------------------------------------------

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

# FIRMS Area API supports 1-5 day requests.
CHUNK_DAYS = 5


# ------------------------------------------------------------
# SPATIAL COVERAGE
# ------------------------------------------------------------
#
# Broad study area.
#
# west, south, east, north
#
# This intentionally includes:
#
#   - Dahej industrial area
#   - industrial fringe
#   - rural/agricultural surroundings
#   - coastal/open areas
#
# so that later PHOENIX classification has
# contrasting spatial contexts.
# ------------------------------------------------------------

STUDY_BBOX = {
    "west": 72.25,
    "south": 21.35,
    "east": 73.00,
    "north": 22.10,
}


# Existing Dahej core used in the earlier POC.
#
# IMPORTANT:
# This is a geographic study zone.
# It is NOT a fire classification.
CORE_BBOX = {
    "west": 72.50,
    "south": 21.60,
    "east": 72.75,
    "north": 21.85,
}


# A slightly wider zone around the core.
FRINGE_BBOX = {
    "west": 72.40,
    "south": 21.50,
    "east": 72.85,
    "north": 21.95,
}


# ------------------------------------------------------------
# REQUEST SETTINGS
# ------------------------------------------------------------

REQUEST_TIMEOUT = 180
MAX_RETRIES = 4

# Be deliberately conservative.
# The FIRMS API has transaction limits, and the previous
# POC run demonstrated that we should not hammer the service.
SLEEP_BETWEEN_REQUESTS = 1.0
SLEEP_AFTER_FAILURE = 10.0


# ------------------------------------------------------------
# OUTPUT FILES
# ------------------------------------------------------------

OBSERVATION_CSV = (
    OUTPUT_DIR
    / "dahej_firms_observations.csv"
)

OBSERVATION_PARQUET = (
    OUTPUT_DIR
    / "dahej_firms_observations.parquet"
)

DAILY_SUMMARY_CSV = (
    OUTPUT_DIR
    / "dahej_firms_daily_summary.csv"
)


# ============================================================
# HELPERS
# ============================================================


def ensure_directories() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for sensor in SENSORS:
        (
            RAW_DIR / sensor
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


def date_chunks(
    start: date,
    end: date,
    chunk_days: int,
):
    """
    Yield inclusive date ranges.

    Example:
        2023-01-01 → 2023-01-05
        2023-01-06 → 2023-01-10
        ...
    """

    current = start

    while current <= end:

        chunk_end = min(
            current
            + timedelta(days=chunk_days - 1),
            end,
        )

        yield current, chunk_end

        current = (
            chunk_end
            + timedelta(days=1)
        )


def bbox_string() -> str:

    return (
        f"{STUDY_BBOX['west']},"
        f"{STUDY_BBOX['south']},"
        f"{STUDY_BBOX['east']},"
        f"{STUDY_BBOX['north']}"
    )


def build_url(
    sensor: str,
    start: date,
    end: date,
) -> str:

    days = (
        end - start
    ).days + 1

    return (
        f"{FIRMS_API_URL}/"
        f"{MAP_KEY}/"
        f"{sensor}/"
        f"{bbox_string()}/"
        f"{days}/"
        f"{start.isoformat()}"
    )


def cache_filename(
    sensor: str,
    start: date,
    end: date,
) -> Path:

    return (
        RAW_DIR
        / sensor
        / f"{sensor}_{start}_{end}.csv"
    )


# ============================================================
# DOWNLOAD
# ============================================================


def download_chunk(
    sensor: str,
    start: date,
    end: date,
) -> Path | None:

    output_file = cache_filename(
        sensor,
        start,
        end,
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------
    #
    # If this exact request was already downloaded,
    # DO NOT hit NASA again.
    # --------------------------------------------------------

    if output_file.exists():

        print(
            f"  CACHE "
            f"{sensor} "
            f"{start} → {end}"
        )

        return output_file

    url = build_url(
        sensor,
        start,
        end,
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        print(
            f"  DOWNLOAD "
            f"{sensor} "
            f"{start} → {end} "
            f"(attempt {attempt})"
        )

        try:

            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": (
                        "PHOENIX-POC/1.0 "
                        "FIRMS dataset builder"
                    )
                },
            )

            response.raise_for_status()

            content = response.content

            # Basic protection against receiving an HTML/API
            # error page with HTTP 200.
            if not content.strip():
                raise RuntimeError(
                    "FIRMS returned an empty response."
                )

            if (
                b"Invalid MAP_KEY"
                in content[:1000]
            ):
                raise RuntimeError(
                    "FIRMS returned Invalid MAP_KEY."
                )

            output_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_file.write_bytes(
                content
            )

            time.sleep(
                SLEEP_BETWEEN_REQUESTS
            )

            return output_file

        except Exception as exc:

            print(
                f"  ERROR: {exc}"
            )

            if attempt < MAX_RETRIES:

                print(
                    f"  Waiting "
                    f"{SLEEP_AFTER_FAILURE}s..."
                )

                time.sleep(
                    SLEEP_AFTER_FAILURE
                )

    print(
        f"  FAILED "
        f"{sensor} "
        f"{start} → {end}"
    )

    return None


# ============================================================
# LOAD + NORMALIZE
# ============================================================


def load_raw_file(
    path: Path,
    sensor: str,
) -> pd.DataFrame:

    try:

        df = pd.read_csv(
            path
        )

    except Exception as exc:

        print(
            f"  Could not read {path}: {exc}"
        )

        return pd.DataFrame()

    if df.empty:
        return df

    # Preserve which API source produced this row.
    df["firms_sensor"] = sensor

    return df


def make_timestamp(
    df: pd.DataFrame,
) -> pd.Series:

    date_part = (
        df["acq_date"]
        .astype(str)
        .str.strip()
    )

    time_part = (
        df["acq_time"]
        .astype(str)
        .str.replace(
            ".0",
            "",
            regex=False,
        )
        .str.zfill(4)
    )

    return pd.to_datetime(
        date_part
        + " "
        + time_part,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )


def confidence_score(
    value,
) -> float:

    value = str(value).lower().strip()

    mapping = {
        "h": 1.0,
        "n": 0.66,
        "l": 0.33,
    }

    return mapping.get(
        value,
        0.0,
    )


def assign_spatial_zone(
    latitude: float,
    longitude: float,
) -> str:

    # Core first.
    if (
        CORE_BBOX["south"]
        <= latitude
        <= CORE_BBOX["north"]
        and
        CORE_BBOX["west"]
        <= longitude
        <= CORE_BBOX["east"]
    ):

        return "dahej_core"

    # Fringe second.
    if (
        FRINGE_BBOX["south"]
        <= latitude
        <= FRINGE_BBOX["north"]
        and
        FRINGE_BBOX["west"]
        <= longitude
        <= FRINGE_BBOX["east"]
    ):

        return "dahej_fringe"

    return "comparison_area"


def make_source_record_id(
    row,
) -> str:

    # Keep the original source identity where available.
    if (
        "source_record_id"
        in row.index
        and pd.notna(
            row["source_record_id"]
        )
    ):

        return str(
            row["source_record_id"]
        )

    raw = (
        f"{row.get('latitude')}|"
        f"{row.get('longitude')}|"
        f"{row.get('acq_date')}|"
        f"{row.get('acq_time')}|"
        f"{row.get('satellite')}|"
        f"{row.get('frp')}|"
        f"{row.get('confidence')}"
    )

    return hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()


def normalize_dataframe(
    frames: list[pd.DataFrame],
) -> pd.DataFrame:

    if not frames:

        return pd.DataFrame()

    df = pd.concat(
        frames,
        ignore_index=True,
    )

    print(
        f"Raw combined rows: {len(df)}"
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    df["timestamp"] = make_timestamp(
        df
    )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "latitude",
        "longitude",
        "bright_ti4",
        "bright_ti5",
        "frp",
        "scan",
        "track",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    df["confidence_raw"] = (
        df["confidence"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    df["confidence_score"] = (
        df["confidence_raw"]
        .apply(confidence_score)
    )

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    df["source"] = "NASA_FIRMS"

    # Don't overwrite FIRMS's own source_record_id.
    if (
        "source_record_id"
        not in df.columns
    ):

        df["source_record_id"] = df.apply(
            make_source_record_id,
            axis=1,
        )

    else:

        missing = (
            df["source_record_id"]
            .isna()
        )

        df.loc[
            missing,
            "source_record_id",
        ] = df.loc[
            missing
        ].apply(
            make_source_record_id,
            axis=1,
        )

    # --------------------------------------------------------
    # Deterministic PHOENIX observation ID
    # --------------------------------------------------------

    def observation_id(row):

        raw = (
            f"{row['source']}|"
            f"{row['source_record_id']}|"
            f"{row['firms_sensor']}"
        )

        return hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()

    df["observation_id"] = df.apply(
        observation_id,
        axis=1,
    )

    # --------------------------------------------------------
    # Remove invalid essential records
    # --------------------------------------------------------

    before = len(df)

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "timestamp",
            "frp",
        ]
    )

    print(
        f"Invalid rows removed: "
        f"{before - len(df)}"
    )

    # --------------------------------------------------------
    # Exact deduplication
    # --------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=[
            "observation_id"
        ]
    )

    print(
        f"Duplicate rows removed: "
        f"{before - len(df)}"
    )

    # --------------------------------------------------------
    # Study-area zone
    # --------------------------------------------------------

    df["spatial_zone"] = [
        assign_spatial_zone(
            latitude,
            longitude,
        )
        for latitude, longitude
        in zip(
            df["latitude"],
            df["longitude"],
        )
    ]

    # --------------------------------------------------------
    # Preserve FIRMS type, but don't treat it as ground truth.
    # --------------------------------------------------------

    if "type" in df.columns:

        df["firms_type_raw"] = (
            df["type"]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# DAILY SUMMARY
# ============================================================


def build_daily_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:

    summary = (
        df.assign(
            date=df["timestamp"].dt.date
        )
        .groupby(
            [
                "date",
                "spatial_zone",
                "firms_sensor",
            ],
            dropna=False,
        )
        .agg(
            observation_count=(
                "observation_id",
                "count",
            ),
            max_frp=(
                "frp",
                "max",
            ),
            mean_frp=(
                "frp",
                "mean",
            ),
            high_confidence_count=(
                "confidence_score",
                lambda x: (
                    x >= 0.9
                ).sum()
            ),
        )
        .reset_index()
    )

    return summary


# ============================================================
# MAIN
# ============================================================


def main():

    print()
    print("==============================================")
    print(" PHOENIX - DAHEJ FIRMS DATASET BUILDER")
    print("==============================================")
    print()

    print(
        f"Period: "
        f"{START_DATE} → {END_DATE}"
    )

    print(
        f"Sensors: "
        f"{', '.join(SENSORS)}"
    )

    print(
        "Study bbox: "
        f"{bbox_string()}"
    )

    print()

    ensure_directories()

    all_frames = []

    total_requests = 0
    successful_requests = 0
    failed_requests = 0

    # --------------------------------------------------------
    # Download/cache
    # --------------------------------------------------------

    for sensor in SENSORS:

        print()
        print(
            f"========== {sensor} =========="
        )

        for start, end in date_chunks(
            START_DATE,
            END_DATE,
            CHUNK_DAYS,
        ):

            total_requests += 1

            path = download_chunk(
                sensor,
                start,
                end,
            )

            if path is None:

                failed_requests += 1
                continue

            successful_requests += 1

            frame = load_raw_file(
                path,
                sensor,
            )

            if not frame.empty:

                all_frames.append(
                    frame
                )

    # --------------------------------------------------------
    # Fail safely.
    # --------------------------------------------------------

    if not all_frames:

        raise RuntimeError(
            "No FIRMS data was downloaded/loaded."
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    df = normalize_dataframe(
        all_frames
    )

    # --------------------------------------------------------
    # Save observation dataset
    # --------------------------------------------------------

    df.to_csv(
        OBSERVATION_CSV,
        index=False,
    )

    # Parquet is optional.
    try:

        df.to_parquet(
            OBSERVATION_PARQUET,
            index=False,
        )

        parquet_status = (
            str(OBSERVATION_PARQUET)
        )

    except Exception as exc:

        parquet_status = (
            f"not created ({exc})"
        )

    # --------------------------------------------------------
    # Daily summary
    # --------------------------------------------------------

    daily = build_daily_summary(
        df
    )

    daily.to_csv(
        DAILY_SUMMARY_CSV,
        index=False,
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("==============================================")
    print(" DATASET BUILD COMPLETE")
    print("==============================================")

    print(
        f"API requests planned:     "
        f"{total_requests}"
    )

    print(
        f"Successful/cache hits:    "
        f"{successful_requests}"
    )

    print(
        f"Failed chunks:            "
        f"{failed_requests}"
    )

    print()
    print(
        f"Observations:             "
        f"{len(df)}"
    )

    print(
        f"Unique observations:      "
        f"{df['observation_id'].nunique()}"
    )

    print(
        f"Date range:               "
        f"{df['timestamp'].min()} → "
        f"{df['timestamp'].max()}"
    )

    print()
    print("Observations by sensor:")

    print(
        df["firms_sensor"]
        .value_counts()
        .to_string()
    )

    print()
    print("Observations by spatial zone:")

    print(
        df["spatial_zone"]
        .value_counts()
        .to_string()
    )

    print()
    print("FRP statistics:")

    print(
        df["frp"]
        .describe()
        .to_string()
    )

    print()
    print("Confidence:")

    print(
        df["confidence_raw"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("Files:")

    print(
        f"  Observations CSV: "
        f"{OBSERVATION_CSV}"
    )

    print(
        f"  Observations Parquet: "
        f"{parquet_status}"
    )

    print(
        f"  Daily summary: "
        f"{DAILY_SUMMARY_CSV}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No industrial/non-industrial labels "
        "were created."
    )

    print(
        "No facility information was used."
    )

    print(
        "The dataset is ready for the next "
        "Thermal Event + spatial-context stage."
    )

    print("==============================================")


if __name__ == "__main__":
    main()