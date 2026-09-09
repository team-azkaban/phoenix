from __future__ import annotations

import hashlib
import os
import time
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.cluster import DBSCAN


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY not found. Put it in phoenix/.env"
    )


START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)

# Products confirmed available for 2025 from your test.
SENSORS = [
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

OUTPUT_ROOT = PROJECT_ROOT / "data" / "region_evaluation"
RAW_ROOT = OUTPUT_ROOT / "raw"
PROCESSED_ROOT = OUTPUT_ROOT / "processed"

RAW_ROOT.mkdir(parents=True, exist_ok=True)
PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Candidate regions
#
# Format:
# west, south, east, north
#
# These are intentionally focused industrial corridors,
# not entire districts.
# ---------------------------------------------------------

REGIONS = {
    "jamnagar": {
        "bbox": (69.90, 22.30, 70.20, 22.55),
        "description": "Jamnagar industrial corridor / GIDC area",
    },

    "dahej_bharuch": {
        "bbox": (72.50, 21.60, 72.75, 21.85),
        "description": "Dahej industrial / PCPIR corridor",
    },

    "ankleshwar_bharuch": {
        "bbox": (72.85, 21.50, 73.15, 21.75),
        "description": "Ankleshwar industrial corridor",
    },

    "mundra": {
        "bbox": (69.55, 22.65, 69.90, 23.00),
        "description": "Mundra port / industrial corridor",
    },

    "visakhapatnam": {
        "bbox": (83.05, 17.55, 83.35, 17.85),
        "description": "Visakhapatnam industrial corridor",
    },

    "paradip": {
        "bbox": (86.50, 20.15, 86.85, 20.45),
        "description": "Paradip port / industrial corridor",
    },
}


# ---------------------------------------------------------
# HTTP session
# ---------------------------------------------------------

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "PHOENIX-POC-region-evaluation/1.0"
    }
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def date_chunks(start: date, end: date, chunk_days: int = 5):
    """
    Generate inclusive date ranges of <= 5 days.
    """
    current = start

    while current <= end:
        chunk_end = min(
            current + timedelta(days=chunk_days - 1),
            end,
        )

        yield current, chunk_end

        current = chunk_end + timedelta(days=1)


def bbox_string(bbox):
    west, south, east, north = bbox
    return f"{west},{south},{east},{north}"


def make_source_record_id(row: pd.Series) -> str:
    """
    Deterministic identifier for a FIRMS observation.

    We retain the original source information in the raw
    dataset and use this hash to help deduplicate.
    """
    values = [
        str(row.get("latitude", "")),
        str(row.get("longitude", "")),
        str(row.get("acq_date", "")),
        str(row.get("acq_time", "")),
        str(row.get("satellite", "")),
        str(row.get("instrument", "")),
        str(row.get("version", "")),
    ]

    raw = "|".join(values)

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def download_firms(
    region_name: str,
    bbox: tuple[float, float, float, float],
    sensor: str,
    chunk_start: date,
    chunk_end: date,
) -> pd.DataFrame:
    """
    Download one FIRMS <=5-day chunk.
    """

    bbox_text = bbox_string(bbox)

    day_range = (chunk_end - chunk_start).days + 1

    url = (
        "https://firms.modaps.eosdis.nasa.gov/"
        f"api/area/csv/{MAP_KEY}/"
        f"{sensor}/{bbox_text}/{day_range}/"
        f"{chunk_start.isoformat()}"
    )

    raw_dir = RAW_ROOT / region_name
    raw_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{sensor}_"
        f"{chunk_start.isoformat()}_"
        f"{chunk_end.isoformat()}.csv"
    )

    output_file = raw_dir / filename

    # Reuse an existing download.
    if output_file.exists():
        print(f"  cached: {output_file.name}")

        try:
            return pd.read_csv(output_file)
        except Exception:
            output_file.unlink()

    print(
        f"  downloading {sensor} "
        f"{chunk_start} -> {chunk_end}"
    )

    response = session.get(url, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"FIRMS request failed "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    output_file.write_text(
        response.text,
        encoding="utf-8",
    )

    text = response.text.strip()

    if not text:
        return pd.DataFrame()

    if text.lower().startswith("error"):
        raise RuntimeError(text)

    try:
        return pd.read_csv(StringIO(text))
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def normalize_firms(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the fields needed for region evaluation.
    """

    if df.empty:
        return df

    df = df.copy()

    # Build timestamp.
    if "acq_date" in df.columns and "acq_time" in df.columns:

        time_string = (
            df["acq_time"]
            .astype(str)
            .str.zfill(4)
        )

        df["timestamp"] = pd.to_datetime(
            df["acq_date"].astype(str)
            + " "
            + time_string.str[:2]
            + ":"
            + time_string.str[2:4],
            errors="coerce",
            utc=True,
        )

    # Numeric fields.
    numeric_columns = [
        "latitude",
        "longitude",
        "frp",
        "bright_ti4",
        "bright_ti5",
        "scan",
        "track",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # Confidence normalization.
    if "confidence" in df.columns:
        df["confidence"] = (
            df["confidence"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

    # Deterministic source record ID.
    df["source_record_id"] = df.apply(
        make_source_record_id,
        axis=1,
    )

    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove exact duplicate source records.

    IMPORTANT:
    We are only deduplicating identical source records here.

    We are NOT collapsing detections from different satellites.
    That will happen later during event clustering.
    """

    if df.empty:
        return df

    before = len(df)

    df = df.drop_duplicates(
        subset=["source_record_id"]
    ).copy()

    after = len(df)

    print(
        f"  deduplication: {before} -> {after}"
    )

    return df


def confidence_score(value):
    """
    Convert FIRMS confidence labels into a numeric score
    only for comparison statistics.
    """

    if pd.isna(value):
        return np.nan

    value = str(value).lower()

    mapping = {
        "l": 0.33,
        "n": 0.50,
        "nominal": 0.50,
        "m": 0.66,
        "h": 1.00,
        "high": 1.00,
    }

    try:
        return float(value)
    except ValueError:
        return mapping.get(value, np.nan)


def preliminary_cluster(df: pd.DataFrame):
    """
    Preliminary region-comparison clustering.

    This is NOT the final PHOENIX event clustering algorithm.

    Approximation:
        ~1 km spatial radius
        no temporal restriction in this first pass

    Later we will implement proper spatial-temporal
    clustering for thermal_events.
    """

    if df.empty or len(df) < 2:
        return 0, 0

    coords = df[
        ["latitude", "longitude"]
    ].dropna().copy()

    if len(coords) < 2:
        return 0, 0

    # Convert degrees to radians.
    coordinates = np.radians(
        coords[["latitude", "longitude"]].values
    )

    # Earth's radius in km.
    earth_radius_km = 6371.0088

    # Approximately 1 km radius.
    eps_km = 1.0

    eps_radians = eps_km / earth_radius_km

    model = DBSCAN(
        eps=eps_radians,
        min_samples=2,
        metric="haversine",
    )

    labels = model.fit_predict(coordinates)

    coords["cluster"] = labels

    valid = coords[
        coords["cluster"] >= 0
    ]

    if valid.empty:
        return 0, 0

    cluster_count = valid["cluster"].nunique()

    cluster_sizes = (
        valid.groupby("cluster")
        .size()
    )

    recurring_clusters = int(
        (cluster_sizes >= 3).sum()
    )

    return (
        int(cluster_count),
        recurring_clusters,
    )


def calculate_statistics(
    region_name: str,
    description: str,
    df: pd.DataFrame,
) -> dict:

    if df.empty:
        return {
            "region": region_name,
            "description": description,
            "observations": 0,
            "active_days": 0,
            "unique_locations": 0,
            "mean_frp": np.nan,
            "median_frp": np.nan,
            "max_frp": np.nan,
            "p90_frp": np.nan,
            "high_frp_count": 0,
            "high_confidence_count": 0,
            "day_count": 0,
            "night_count": 0,
            "clusters": 0,
            "recurring_clusters": 0,
        }

    df = df.copy()

    observations = len(df)

    active_days = (
        df["timestamp"]
        .dt.date
        .nunique()
        if "timestamp" in df.columns
        else 0
    )

    # Rounded spatial locations.
    unique_locations = (
        df[["latitude", "longitude"]]
        .dropna()
        .assign(
            latitude=lambda x: x["latitude"].round(3),
            longitude=lambda x: x["longitude"].round(3),
        )
        .drop_duplicates()
        .shape[0]
    )

    if "frp" in df.columns:
        frp = df["frp"].dropna()

        mean_frp = (
            float(frp.mean())
            if not frp.empty
            else np.nan
        )

        median_frp = (
            float(frp.median())
            if not frp.empty
            else np.nan
        )

        max_frp = (
            float(frp.max())
            if not frp.empty
            else np.nan
        )

        p90_frp = (
            float(frp.quantile(0.90))
            if not frp.empty
            else np.nan
        )

        # This is only a comparison threshold.
        # It is NOT a PHOENIX risk threshold.
        high_frp_count = int(
            (frp >= 20).sum()
        )

    else:
        mean_frp = np.nan
        median_frp = np.nan
        max_frp = np.nan
        p90_frp = np.nan
        high_frp_count = 0

    if "confidence" in df.columns:
        confidence_numeric = (
            df["confidence"]
            .apply(confidence_score)
        )

        high_confidence_count = int(
            (confidence_numeric >= 0.90).sum()
        )

    else:
        high_confidence_count = 0

    if "daynight" in df.columns:
        day_count = int(
            (
                df["daynight"]
                .astype(str)
                .str.upper()
                == "D"
            ).sum()
        )

        night_count = int(
            (
                df["daynight"]
                .astype(str)
                .str.upper()
                == "N"
            ).sum()
        )

    else:
        day_count = 0
        night_count = 0

    clusters, recurring_clusters = (
        preliminary_cluster(df)
    )

    return {
        "region": region_name,
        "description": description,
        "observations": observations,
        "active_days": active_days,
        "unique_locations": unique_locations,
        "mean_frp": mean_frp,
        "median_frp": median_frp,
        "max_frp": max_frp,
        "p90_frp": p90_frp,
        "high_frp_count": high_frp_count,
        "high_confidence_count": high_confidence_count,
        "day_count": day_count,
        "night_count": night_count,
        "clusters": clusters,
        "recurring_clusters": recurring_clusters,
    }


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("PHOENIX — FIRMS REGION EVALUATION")
    print("=" * 70)

    print()
    print(f"Analysis period: {START_DATE} -> {END_DATE}")
    print(f"Sensors: {', '.join(SENSORS)}")
    print(f"Regions: {len(REGIONS)}")
    print()

    summaries = []

    for region_name, region_config in REGIONS.items():

        print()
        print("-" * 70)
        print(f"REGION: {region_name}")
        print(region_config["description"])
        print("-" * 70)

        region_frames = []

        for sensor in SENSORS:

            for chunk_start, chunk_end in date_chunks(
                START_DATE,
                END_DATE,
                chunk_days=5,
            ):

                try:

                    chunk_df = download_firms(
                        region_name=region_name,
                        bbox=region_config["bbox"],
                        sensor=sensor,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end,
                    )

                    if not chunk_df.empty:

                        chunk_df["firms_sensor"] = sensor

                        region_frames.append(
                            chunk_df
                        )

                    # Be conservative with API request rate.
                    time.sleep(0.25)

                except Exception as exc:

                    print(
                        f"  ERROR: {sensor} "
                        f"{chunk_start}: {exc}"
                    )

        if not region_frames:

            print("  No observations returned.")

            summaries.append(
                calculate_statistics(
                    region_name,
                    region_config["description"],
                    pd.DataFrame(),
                )
            )

            continue

        region_df = pd.concat(
            region_frames,
            ignore_index=True,
        )

        print(
            f"\n  Raw combined rows: "
            f"{len(region_df)}"
        )

        region_df = normalize_firms(
            region_df
        )

        region_df = deduplicate(
            region_df
        )

        # Save normalized evaluation dataset.
        output_file = (
            PROCESSED_ROOT
            / f"{region_name}_2025.csv"
        )

        region_df.to_csv(
            output_file,
            index=False,
        )

        print(
            f"  Saved: {output_file}"
        )

        stats = calculate_statistics(
            region_name,
            region_config["description"],
            region_df,
        )

        summaries.append(stats)

        print()
        print("  Statistics:")
        print(
            f"    observations:        "
            f"{stats['observations']}"
        )
        print(
            f"    active days:         "
            f"{stats['active_days']}"
        )
        print(
            f"    unique locations:    "
            f"{stats['unique_locations']}"
        )
        print(
            f"    mean FRP:            "
            f"{stats['mean_frp']:.2f}"
        )
        print(
            f"    max FRP:             "
            f"{stats['max_frp']:.2f}"
        )
        print(
            f"    p90 FRP:             "
            f"{stats['p90_frp']:.2f}"
        )
        print(
            f"    high FRP >=20:       "
            f"{stats['high_frp_count']}"
        )
        print(
            f"    high confidence:     "
            f"{stats['high_confidence_count']}"
        )
        print(
            f"    preliminary clusters:"
            f" {stats['clusters']}"
        )
        print(
            f"    recurring clusters:  "
            f"{stats['recurring_clusters']}"
        )

    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    summary_df = pd.DataFrame(
        summaries
    )

    summary_file = (
        PROCESSED_ROOT
        / "region_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
    )

    print()
    print("=" * 70)
    print("REGION SUMMARY")
    print("=" * 70)

    display_columns = [
        "region",
        "observations",
        "active_days",
        "unique_locations",
        "mean_frp",
        "max_frp",
        "high_frp_count",
        "high_confidence_count",
        "clusters",
        "recurring_clusters",
    ]

    print(
        summary_df[
            display_columns
        ].to_string(index=False)
    )

    print()
    print(
        f"Saved summary: {summary_file}"
    )

    print()
    print(
        "IMPORTANT: This is a REGION EVALUATION only."
    )
    print(
        "Do not load these evaluation CSVs into "
        "thermal_observations yet."
    )


if __name__ == "__main__":
    main()