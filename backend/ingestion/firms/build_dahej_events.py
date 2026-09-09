from __future__ import annotations

from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd


# ============================================================
# PHOENIX - DAHEJ THERMAL EVENT BUILDER
# ============================================================
#
# Input:
#   data/firms/dahej/dahej_firms_observations.csv
#
# Output:
#   data/firms/dahej/dahej_candidate_events.csv
#   data/firms/dahej/dahej_event_observations.csv
#
# Event definition for POC:
#
#   1. Observations must be <= 1 km from the event anchor
#   2. Observations must be <= 24 hours from previous observation
#   3. An event episode cannot exceed 48 hours
#
# IMPORTANT:
# - The spatial anchor NEVER moves.
# - This prevents long-distance spatial chaining.
# - Single-observation events are retained.
# - No classification is performed here.
# ============================================================


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "data/firms/dahej/dahej_firms_observations.csv"
)

OUTPUT_EVENTS = Path(
    "data/firms/dahej/dahej_candidate_events.csv"
)

OUTPUT_MAPPING = Path(
    "data/firms/dahej/dahej_event_observations.csv"
)


# ============================================================
# EVENT PARAMETERS
# ============================================================

MAX_DISTANCE_KM = 1.0

MAX_GAP_HOURS = 24.0

MAX_EVENT_DURATION_HOURS = 48.0


# ============================================================
# HELPERS
# ============================================================

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two coordinates.
    """

    earth_radius_km = 6371.0088

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return earth_radius_km * c


def safe_mode(series: pd.Series):
    """
    Return the most common value.
    """

    values = series.dropna()

    if values.empty:
        return None

    modes = values.mode()

    if modes.empty:
        return None

    return modes.iloc[0]


# ============================================================
# LOAD
# ============================================================

print("=" * 72)
print("PHOENIX - DAHEJ THERMAL EVENT BUILDER")
print("=" * 72)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file does not exist: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"\nInput file:")
print(f"  {INPUT_FILE}")

print(f"\nInput observations:")
print(f"  {len(df):,}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "observation_id",
    "timestamp",
    "latitude",
    "longitude",
    "frp",
    "confidence_score",
    "firms_sensor",
    "satellite",
    "daynight",
    "spatial_zone",
]

missing = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing:

    raise ValueError(
        "Missing required columns:\n"
        + "\n".join(
            f"  - {column}"
            for column in missing
        )
    )


# ============================================================
# TYPE NORMALIZATION
# ============================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True,
    errors="coerce",
)

for column in [
    "latitude",
    "longitude",
    "frp",
    "confidence_score",
]:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )


before = len(df)

df = df.dropna(
    subset=[
        "observation_id",
        "timestamp",
        "latitude",
        "longitude",
    ]
).copy()

removed = before - len(df)

print(f"\nInvalid observations removed:")
print(f"  {removed:,}")


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "timestamp",
        "observation_id",
    ]
).reset_index(drop=True)


# ============================================================
# CONFIGURATION
# ============================================================

print("\nEvent configuration:")
print(
    f"  Spatial radius:       {MAX_DISTANCE_KM:.1f} km"
)

print(
    f"  Maximum gap:          {MAX_GAP_HOURS:.1f} hours"
)

print(
    f"  Maximum duration:     {MAX_EVENT_DURATION_HOURS:.1f} hours"
)

print(
    "\nSpatial anchor:"
)

print(
    "  FIXED - event centroid will NOT drift"
)


# ============================================================
# EVENT CLUSTERING
# ============================================================
#
# Unlike the previous version:
#
#     OLD:
#       event centroid moved after every observation
#
#     NEW:
#       event anchor = first observation
#
# This prevents:
#
#     A -> B -> C -> D -> E
#
# from gradually walking across the industrial area.
#
# An observation joins an event only when:
#
#     distance(first observation, new observation) <= 1 km
#
# AND
#
#     new timestamp - previous observation <= 24 hours
#
# AND
#
#     total event duration <= 48 hours
#
# ============================================================

events = []

observation_to_event = {}


for row in df.itertuples(index=False):

    timestamp = row.timestamp

    latitude = float(row.latitude)

    longitude = float(row.longitude)

    assigned_event = None

    best_distance = None

    # --------------------------------------------------------
    # Search compatible existing events
    # --------------------------------------------------------

    for event in events:

        # Because the dataframe is chronological,
        # events whose last observation is too old cannot
        # accept this observation.
        gap_hours = (
            timestamp - event["last_seen"]
        ).total_seconds() / 3600.0

        if gap_hours < 0:
            continue

        if gap_hours > MAX_GAP_HOURS:
            continue

        # Total event duration
        duration_hours = (
            timestamp - event["first_seen"]
        ).total_seconds() / 3600.0

        if duration_hours > MAX_EVENT_DURATION_HOURS:
            continue

        # IMPORTANT:
        # Compare against the FIXED event anchor.
        distance_km = haversine_km(
            latitude,
            longitude,
            event["anchor_latitude"],
            event["anchor_longitude"],
        )

        if distance_km > MAX_DISTANCE_KM:
            continue

        if (
            best_distance is None
            or distance_km < best_distance
        ):

            assigned_event = event

            best_distance = distance_km

    # --------------------------------------------------------
    # Existing event
    # --------------------------------------------------------

    if assigned_event is not None:

        assigned_event["last_seen"] = timestamp

        assigned_event["observation_count"] += 1

        assigned_event["observation_ids"].append(
            row.observation_id
        )

        observation_to_event[
            row.observation_id
        ] = assigned_event["event_id"]

    # --------------------------------------------------------
    # New event
    # --------------------------------------------------------

    else:

        event_number = len(events) + 1

        event_id = (
            f"EVT-DAHEJ-{event_number:05d}"
        )

        new_event = {

            "event_id": event_id,

            "first_seen": timestamp,

            "last_seen": timestamp,

            # FIXED ANCHOR
            "anchor_latitude": latitude,

            "anchor_longitude": longitude,

            "observation_count": 1,

            "observation_ids": [
                row.observation_id
            ],
        }

        events.append(new_event)

        observation_to_event[
            row.observation_id
        ] = event_id


print(
    f"\nCandidate event episodes created:"
)

print(
    f"  {len(events):,}"
)


# ============================================================
# BUILD EVENT DATAFRAME
# ============================================================

event_rows = []


for event in events:

    observation_ids = event[
        "observation_ids"
    ]

    event_obs = df[
        df["observation_id"].isin(
            observation_ids
        )
    ].copy()

    event_obs = event_obs.sort_values(
        "timestamp"
    )

    first_seen = event_obs[
        "timestamp"
    ].min()

    last_seen = event_obs[
        "timestamp"
    ].max()

    duration_hours = (
        last_seen - first_seen
    ).total_seconds() / 3600.0

    # --------------------------------------------------------
    # Event centroid
    # --------------------------------------------------------

    event_latitude = event_obs[
        "latitude"
    ].mean()

    event_longitude = event_obs[
        "longitude"
    ].mean()

    # --------------------------------------------------------
    # Spatial extent
    # --------------------------------------------------------

    distances = []

    for observation in event_obs.itertuples():

        distance = haversine_km(
            event["anchor_latitude"],
            event["anchor_longitude"],
            float(observation.latitude),
            float(observation.longitude),
        )

        distances.append(distance)

    spatial_extent_km = (
        max(distances)
        if distances
        else 0.0
    )

    # --------------------------------------------------------
    # Temporal recurrence
    # --------------------------------------------------------

    recurrence_days = (
        event_obs["timestamp"]
        .dt.floor("D")
        .nunique()
    )

    # --------------------------------------------------------
    # Sensors
    # --------------------------------------------------------

    sensors = (
        event_obs[
            "firms_sensor"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    satellites = (
        event_obs[
            "satellite"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # Day/night
    # --------------------------------------------------------

    day_count = int(
        event_obs[
            "daynight"
        ]
        .astype(str)
        .str.upper()
        .eq("D")
        .sum()
    )

    night_count = int(
        event_obs[
            "daynight"
        ]
        .astype(str)
        .str.upper()
        .eq("N")
        .sum()
    )

    # --------------------------------------------------------
    # FRP
    # --------------------------------------------------------

    max_frp = event_obs[
        "frp"
    ].max()

    mean_frp = event_obs[
        "frp"
    ].mean()

    current_frp = event_obs.iloc[-1][
        "frp"
    ]

    frp_std = event_obs[
        "frp"
    ].std()

    # --------------------------------------------------------
    # FRP growth
    # --------------------------------------------------------

    if len(event_obs) >= 2:

        first_frp = event_obs.iloc[0][
            "frp"
        ]

        last_frp = event_obs.iloc[-1][
            "frp"
        ]

        if pd.notna(first_frp) and first_frp != 0:

            frp_growth = (
                last_frp - first_frp
            ) / abs(first_frp)

        else:

            frp_growth = None

    else:

        frp_growth = None

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    max_confidence = event_obs[
        "confidence_score"
    ].max()

    mean_confidence = event_obs[
        "confidence_score"
    ].mean()

    high_confidence_count = int(
        (
            event_obs[
                "confidence_score"
            ] >= 0.9
        ).sum()
    )

    # --------------------------------------------------------
    # High FRP
    # --------------------------------------------------------

    high_frp_count = int(
        (
            event_obs[
                "frp"
            ] >= 20
        ).sum()
    )

    # --------------------------------------------------------
    # Build event record
    # --------------------------------------------------------

    event_rows.append(
        {
            "event_id": event[
                "event_id"
            ],

            "first_seen": first_seen,

            "last_seen": last_seen,

            "latitude": event_latitude,

            "longitude": event_longitude,

            "anchor_latitude": event[
                "anchor_latitude"
            ],

            "anchor_longitude": event[
                "anchor_longitude"
            ],

            "observation_count": len(
                event_obs
            ),

            "max_frp": max_frp,

            "mean_frp": mean_frp,

            "current_frp": current_frp,

            "frp_std": frp_std,

            "frp_growth": frp_growth,

            "max_confidence": max_confidence,

            "mean_confidence": mean_confidence,

            "high_confidence_count": (
                high_confidence_count
            ),

            "high_frp_count": (
                high_frp_count
            ),

            "sensor_count": len(
                sensors
            ),

            "sensors": ";".join(
                sorted(sensors)
            ),

            "satellites": ";".join(
                sorted(satellites)
            ),

            "day_count": day_count,

            "night_count": night_count,

            "duration_hours": (
                duration_hours
            ),

            "recurrence_days": (
                recurrence_days
            ),

            "spatial_extent_km": (
                spatial_extent_km
            ),

            "spatial_zone": safe_mode(
                event_obs[
                    "spatial_zone"
                ]
            ),

            # Classification deliberately
            # left NULL at this stage.
            "classification": None,

            "classification_confidence": None,
        }
    )


events_df = pd.DataFrame(
    event_rows
)


# ============================================================
# EVENT → OBSERVATION MAPPING
# ============================================================

mapping_df = pd.DataFrame(
    [
        {
            "event_id": event_id,
            "observation_id": observation_id,
        }

        for observation_id, event_id
        in observation_to_event.items()
    ]
)


# ============================================================
# VALIDATION
# ============================================================

print("\nValidation:")

print(
    f"  Observations: "
    f"{len(df):,}"
)

print(
    f"  Event records: "
    f"{len(events_df):,}"
)

print(
    f"  Mapping records: "
    f"{len(mapping_df):,}"
)

print(
    f"  Unmapped observations: "
    f"{len(df) - len(mapping_df):,}"
)


# ============================================================
# DISTRIBUTION
# ============================================================

print("\nObservation count distribution:")

distribution = (
    events_df[
        "observation_count"
    ]
    .value_counts()
    .sort_index()
)

for observation_count, count in distribution.items():

    if observation_count <= 10:

        label = str(observation_count)

    elif observation_count <= 20:

        label = "11-20"

    elif observation_count <= 50:

        label = "21-50"

    elif observation_count <= 100:

        label = "51-100"

    else:

        label = "100+"

    print(
        f"  {label:>8}: {count:,}"
    )


# ============================================================
# EVENT STATISTICS
# ============================================================

print("\nEvent statistics:")

print(
    f"  Median duration: "
    f"{events_df['duration_hours'].median():.2f} hours"
)

print(
    f"  Maximum duration: "
    f"{events_df['duration_hours'].max():.2f} hours"
)

print(
    f"  Median observations/event: "
    f"{events_df['observation_count'].median():.1f}"
)

print(
    f"  Maximum observations/event: "
    f"{events_df['observation_count'].max():,}"
)

print(
    f"  Maximum spatial extent: "
    f"{events_df['spatial_extent_km'].max():.3f} km"
)

print(
    f"  Maximum FRP: "
    f"{events_df['max_frp'].max():.2f} MW"
)


# ============================================================
# ZONE DISTRIBUTION
# ============================================================

print("\nEvents by spatial zone:")

print(
    events_df[
        "spatial_zone"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)


# ============================================================
# HIGH FRP EVENTS
# ============================================================

print(
    "\nTop 15 events by maximum FRP:"
)

top_events = (
    events_df
    .sort_values(
        "max_frp",
        ascending=False,
    )
    .head(15)
)

print(
    top_events[
        [
            "event_id",
            "first_seen",
            "last_seen",
            "observation_count",
            "max_frp",
            "mean_frp",
            "max_confidence",
            "duration_hours",
            "spatial_extent_km",
            "spatial_zone",
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_EVENTS.parent.mkdir(
    parents=True,
    exist_ok=True,
)

events_df.to_csv(
    OUTPUT_EVENTS,
    index=False,
)

mapping_df.to_csv(
    OUTPUT_MAPPING,
    index=False,
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 72)
print("FINAL EVENT BUILD COMPLETE")
print("=" * 72)

print("\nCreated:")

print(
    f"  {OUTPUT_EVENTS}"
)

print(
    f"  {OUTPUT_MAPPING}"
)

print("\nEvent model is now ready for:")
print("  1. PostGIS thermal_events")
print("  2. event_observations")
print("  3. facility enrichment")
print("  4. classification")

print("\nClassification has NOT been performed.")

print("=" * 72)