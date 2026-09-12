from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd

from db.database import SessionLocal
from db.models.thermal_event import ThermalEvent


PROJECT_ROOT = Path(__file__).resolve().parents[3]

FLARE_FILE = (
    PROJECT_ROOT
    / "data"
    / "context"
    / "flare"
    / "dahej_flare_context.csv"
)


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two coordinates in km."""
    earth_radius_km = 6371.0088

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius_km * atan2(sqrt(a), sqrt(1 - a))


def load_flare_context():
    if not FLARE_FILE.exists():
        raise FileNotFoundError(
            f"Flare context file not found:\n{FLARE_FILE}"
        )

    df = pd.read_csv(FLARE_FILE)

    required_columns = [
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

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    return df


def load_events():
    db = SessionLocal()

    try:
        events = (
            db.query(ThermalEvent)
            .filter(
                ThermalEvent.latitude.isnot(None),
                ThermalEvent.longitude.isnot(None),
            )
            .all()
        )

        rows = []

        for event in events:
            rows.append(
                {
                    "event_id": str(event.event_id),
                    "latitude": float(event.latitude),
                    "longitude": float(event.longitude),
                    "current_frp": (
                        float(event.current_frp)
                        if event.current_frp is not None
                        else None
                    ),
                    "max_frp": (
                        float(event.max_frp)
                        if event.max_frp is not None
                        else None
                    ),
                    "mean_frp": (
                        float(event.mean_frp)
                        if event.mean_frp is not None
                        else None
                    ),
                    "observation_count": (
                        int(event.observation_count)
                        if event.observation_count is not None
                        else 0
                    ),
                    "duration": (
                        float(event.duration)
                        if event.duration is not None
                        else 0.0
                    ),
                    "landcover_class": event.landcover_class,
                    "facility_type": event.facility_type,
                    "facility_distance_m": (
                        float(event.facility_distance_m)
                        if event.facility_distance_m is not None
                        else None
                    ),
                }
            )

        return pd.DataFrame(rows)

    finally:
        db.close()


def assign_distance_band(distance_m):
    if distance_m < 500:
        return "<500m"
    elif distance_m < 1000:
        return "500m-1km"
    elif distance_m < 1500:
        return "1km-1.5km"
    elif distance_m < 2000:
        return "1.5km-2km"
    elif distance_m < 5000:
        return "2km-5km"
    else:
        return ">5km"


def main():
    print("=" * 60)
    print("PHOENIX FLARE / INDUSTRIAL-SOURCE CONTEXT ANALYSIS")
    print("=" * 60)

    flare_df = load_flare_context()
    events_df = load_events()

    print(f"\nFlare/source contexts: {len(flare_df)}")
    print(f"Thermal events:        {len(events_df)}")

    print("\n" + "=" * 60)
    print("FLARE / SOURCE CONTEXTS")
    print("=" * 60)

    for _, flare in flare_df.iterrows():
        print(
            f"\n{flare['context_id']} - {flare['name']}"
        )
        print(
            f"  Type:             {flare['context_type']}"
        )
        print(
            f"  Facility type:    {flare['facility_type']}"
        )
        print(
            f"  Coordinates:      "
            f"{float(flare['latitude']):.6f}, "
            f"{float(flare['longitude']):.6f}"
        )
        print(
            f"  Context radius:   "
            f"{float(flare['context_radius_m']):.0f} m"
        )
        print(
            f"  Confidence:       {flare['confidence']}"
        )
        print(
            f"  Approximate:      {flare['is_approximate']}"
        )

    results = []

    for _, event in events_df.iterrows():
        for _, flare in flare_df.iterrows():
            distance_m = (
                haversine_km(
                    event["latitude"],
                    event["longitude"],
                    flare["latitude"],
                    flare["longitude"],
                )
                * 1000
            )

            results.append(
                {
                    "event_id": event["event_id"],
                    "flare_id": flare["context_id"],
                    "flare_name": flare["name"],
                    "facility_type": flare["facility_type"],
                    "distance_m": distance_m,
                    "max_frp": event["max_frp"],
                    "mean_frp": event["mean_frp"],
                    "observation_count": event["observation_count"],
                    "duration": event["duration"],
                    "landcover_class": event["landcover_class"],
                }
            )

    results_df = pd.DataFrame(results)

    # ---------------------------------------------------------
    # NEAREST FLARE/SOURCE PER EVENT
    # ---------------------------------------------------------

    nearest_df = (
        results_df
        .sort_values("distance_m")
        .groupby("event_id", as_index=False)
        .first()
    )

    print("\n" + "=" * 60)
    print("DISTANCE BANDS TO NEAREST FLARE/SOURCE")
    print("=" * 60)

    nearest_df["distance_band"] = nearest_df[
        "distance_m"
    ].apply(assign_distance_band)

    band_order = [
        "<500m",
        "500m-1km",
        "1km-1.5km",
        "1.5km-2km",
        "2km-5km",
        ">5km",
    ]

    band_counts = (
        nearest_df["distance_band"]
        .value_counts()
        .reindex(band_order, fill_value=0)
    )

    for band, count in band_counts.items():
        print(f"  {band:<12} {count}")

    # ---------------------------------------------------------
    # EVENTS WITHIN DOCUMENTED CONTEXT RADIUS
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("EVENTS WITHIN DOCUMENTED FLARE/SOURCE RADIUS")
    print("=" * 60)

    for _, flare in flare_df.iterrows():
        subset = results_df[
            (results_df["flare_id"] == flare["context_id"])
            & (
                results_df["distance_m"]
                <= float(flare["context_radius_m"])
            )
        ]

        print(
            f"\n{flare['context_id']} - {flare['name']}"
        )
        print(
            f"  Approximate radius: "
            f"{float(flare['context_radius_m']):.0f} m"
        )
        print(
            f"  Events within radius: {len(subset)}"
        )

    # ---------------------------------------------------------
    # CLOSEST EVENTS
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("30 CLOSEST EVENTS TO FLARE / INDUSTRIAL SOURCES")
    print("=" * 60)

    closest = (
        results_df
        .sort_values("distance_m")
        .drop_duplicates("event_id")
        .head(30)
    )

    for _, row in closest.iterrows():
        frp = (
            row["max_frp"]
            if pd.notna(row["max_frp"])
            else row["mean_frp"]
        )

        print(
            f"  {row['distance_m']:7.1f} m | "
            f"FRP {frp:6.2f} | "
            f"{str(row['landcover_class']):25} | "
            f"{row['flare_name']} | "
            f"{row['event_id']}"
        )

    # ---------------------------------------------------------
    # HIGH-FRP EVENTS WITHIN 2 KM
    # ---------------------------------------------------------

    high_frp = results_df[
        results_df["distance_m"] <= 2000
    ].copy()

    high_frp = (
        high_frp
        .sort_values(
            ["max_frp", "distance_m"],
            ascending=[False, True],
        )
        .drop_duplicates("event_id")
    )

    print("\n" + "=" * 60)
    print("HIGH-FRP EVENTS WITHIN 2 KM")
    print("=" * 60)

    if high_frp.empty:
        print("  No events found.")
    else:
        for _, row in high_frp.iterrows():
            frp = (
                row["max_frp"]
                if pd.notna(row["max_frp"])
                else row["mean_frp"]
            )

            print(
                f"  {row['distance_m']:7.1f} m | "
                f"FRP {frp:6.2f} | "
                f"{str(row['landcover_class']):25} | "
                f"{row['flare_name']} | "
                f"{row['event_id']}"
            )

    # ---------------------------------------------------------
    # EVENTS BY FLARE CONTEXT
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("EVENTS BY FLARE / INDUSTRIAL-SOURCE CONTEXT")
    print("=" * 60)

    for _, flare in flare_df.iterrows():
        context = results_df[
            results_df["flare_id"] == flare["context_id"]
        ]

        radius = float(flare["context_radius_m"])

        within = context[
            context["distance_m"] <= radius
        ]

        within_2km = context[
            context["distance_m"] <= 2000
        ]

        print(
            f"\n{flare['context_id']} - "
            f"{flare['name']}"
        )
        print(
            f"  Within documented radius: "
            f"{len(within)}"
        )
        print(
            f"  Within 2 km:             "
            f"{len(within_2km)}"
        )

        if not within_2km.empty:
            print(
                f"  Maximum FRP within 2 km: "
                f"{within_2km['max_frp'].max():.2f}"
            )

            print(
                f"  Mean FRP within 2 km:    "
                f"{within_2km['max_frp'].mean():.2f}"
            )

    # ---------------------------------------------------------
    # POTENTIAL FLARE CANDIDATES
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("POTENTIAL FLARE CANDIDATES")
    print("=" * 60)

    candidates = nearest_df[
        (nearest_df["distance_m"] <= 2000)
        & (nearest_df["max_frp"] >= 5)
    ].copy()

    candidates = candidates.sort_values(
        ["max_frp", "distance_m"],
        ascending=[False, True],
    )

    if candidates.empty:
        print(
            "  No events satisfy the exploratory "
            "distance/FRP threshold."
        )
    else:
        print(
            "  NOTE: These are candidates only; "
            "they are NOT classified as gas flares."
        )

        for _, row in candidates.iterrows():
            print(
                f"  {row['distance_m']:7.1f} m | "
                f"FRP {row['max_frp']:6.2f} | "
                f"{row['flare_name']} | "
                f"{row['event_id']}"
            )

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()