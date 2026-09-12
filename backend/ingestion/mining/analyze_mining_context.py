from pathlib import Path
import csv
import math

from sqlalchemy import text

from db.database import SessionLocal


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MINING_CSV = (
    PROJECT_ROOT
    / "data"
    / "context"
    / "mining"
    / "dahej_mining_context.csv"
)


# -------------------------------------------------------------------
# Study configuration
# -------------------------------------------------------------------

# These are the approximate context radii we want to inspect.
DISTANCE_BANDS = [
    ("within_300m", 300),
    ("within_500m", 500),
    ("within_1km", 1000),
    ("within_2km", 2000),
    ("within_5km", 5000),
]


# -------------------------------------------------------------------
# Distance calculation
# -------------------------------------------------------------------

def haversine_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two WGS84 coordinates.

    Returns distance in metres.
    """

    earth_radius_m = 6_371_000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius_m * c


# -------------------------------------------------------------------
# Load mining contexts
# -------------------------------------------------------------------

def load_mining_contexts():

    if not MINING_CSV.exists():
        raise FileNotFoundError(
            f"Mining context CSV not found:\n{MINING_CSV}"
        )

    contexts = []

    with MINING_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            contexts.append(
                {
                    "context_id": row["context_id"],
                    "name": row["name"],
                    "context_type": row["context_type"],
                    "material": row["material"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "lease_area_ha": float(
                        row["lease_area_ha"]
                    ),
                    "context_radius_m": float(
                        row["context_radius_m"]
                    ),
                    "source": row["source"],
                    "source_type": row["source_type"],
                    "confidence": row["confidence"],
                    "is_approximate": (
                        row["is_approximate"].lower() == "true"
                    ),
                }
            )

    return contexts


# -------------------------------------------------------------------
# Main analysis
# -------------------------------------------------------------------

def main():

    print("Mining-context analysis started.")
    print(f"Mining CSV: {MINING_CSV}")

    contexts = load_mining_contexts()

    print(f"Mining contexts loaded: {len(contexts)}")

    for context in contexts:
        print(
            f"  {context['context_id']}: "
            f"{context['name']} "
            f"({context['latitude']}, "
            f"{context['longitude']})"
        )

    db = SessionLocal()

    try:

        events = db.execute(
            text(
                """
                SELECT
                    event_id,
                    latitude,
                    longitude,
                    max_frp,
                    duration,
                    observation_count,
                    landcover_class,
                    facility_type,
                    facility_distance_m
                FROM thermal_events
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                ORDER BY event_id
                """
            )
        ).mappings().all()

        print()
        print(f"Thermal events loaded: {len(events)}")

        # -----------------------------------------------------------
        # Calculate nearest mining context for each event
        # -----------------------------------------------------------

        results = []

        for event in events:

            event_lat = float(event["latitude"])
            event_lon = float(event["longitude"])

            nearest_context = None
            nearest_distance = float("inf")

            for context in contexts:

                distance = haversine_distance_m(
                    event_lat,
                    event_lon,
                    context["latitude"],
                    context["longitude"],
                )

                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_context = context

            results.append(
                {
                    "event_id": event["event_id"],
                    "latitude": event_lat,
                    "longitude": event_lon,
                    "nearest_context": nearest_context,
                    "distance_m": nearest_distance,
                    "max_frp": event["max_frp"],
                    "duration": event["duration"],
                    "observation_count": event["observation_count"],
                    "landcover_class": event["landcover_class"],
                    "facility_type": event["facility_type"],
                    "facility_distance_m": event[
                        "facility_distance_m"
                    ],
                }
            )

        # -----------------------------------------------------------
        # Distance-band analysis
        # -----------------------------------------------------------

        print()
        print("=" * 60)
        print("MINING CONTEXT DISTANCE DISTRIBUTION")
        print("=" * 60)

        for label, threshold in DISTANCE_BANDS:

            count = sum(
                result["distance_m"] <= threshold
                for result in results
            )

            print(
                f"{label:18s}: {count:5d} events"
            )

        beyond_5km = sum(
            result["distance_m"] > 5000
            for result in results
        )

        print(
            f"{'beyond_5km':18s}: {beyond_5km:5d} events"
        )

        # -----------------------------------------------------------
        # Show closest events
        # -----------------------------------------------------------

        closest = sorted(
            results,
            key=lambda x: x["distance_m"],
        )[:30]

        print()
        print("=" * 60)
        print("30 EVENTS CLOSEST TO MINING CONTEXT")
        print("=" * 60)

        for result in closest:

            context = result["nearest_context"]

            print(
                f"\nEvent: {result['event_id']}"
            )

            print(
                f"  Distance: "
                f"{result['distance_m']:.1f} m"
            )

            print(
                f"  Mining context: "
                f"{context['name']}"
            )

            print(
                f"  Event location: "
                f"{result['latitude']:.6f}, "
                f"{result['longitude']:.6f}"
            )

            print(
                f"  Max FRP: "
                f"{result['max_frp']}"
            )

            print(
                f"  Duration: "
                f"{result['duration']} h"
            )

            print(
                f"  Observations: "
                f"{result['observation_count']}"
            )

            print(
                f"  Land cover: "
                f"{result['landcover_class']}"
            )

            print(
                f"  Facility type: "
                f"{result['facility_type']}"
            )

            print(
                f"  Facility distance: "
                f"{result['facility_distance_m']} m"
            )

        # -----------------------------------------------------------
        # High-FRP events near mining context
        # -----------------------------------------------------------

        high_frp_nearby = [
            result
            for result in results
            if result["distance_m"] <= 2000
            and result["max_frp"] is not None
        ]

        high_frp_nearby.sort(
            key=lambda x: float(x["max_frp"]),
            reverse=True,
        )

        print()
        print("=" * 60)
        print("HIGH-FRP EVENTS WITHIN 2 KM")
        print("=" * 60)

        if not high_frp_nearby:
            print("No events found within 2 km.")

        else:

            for result in high_frp_nearby[:20]:

                context = result["nearest_context"]

                print(
                    f"{result['distance_m']:8.1f} m | "
                    f"FRP {float(result['max_frp']):6.2f} | "
                    f"{result['landcover_class']:25s} | "
                    f"{context['name']} | "
                    f"{result['event_id']}"
                )

        # -----------------------------------------------------------
        # Summary by mining context
        # -----------------------------------------------------------

        print()
        print("=" * 60)
        print("EVENTS BY MINING CONTEXT")
        print("=" * 60)

        for context in contexts:

            context_results = [
                result
                for result in results
                if result["nearest_context"]["context_id"]
                == context["context_id"]
            ]

            within_radius = [
                result
                for result in context_results
                if result["distance_m"]
                <= context["context_radius_m"]
            ]

            print(
                f"\n{context['context_id']} - "
                f"{context['name']}"
            )

            print(
                f"  Approximate radius: "
                f"{context['context_radius_m']:.0f} m"
            )

            print(
                f"  Events within radius: "
                f"{len(within_radius)}"
            )

            if within_radius:

                max_frp_values = [
                    float(result["max_frp"])
                    for result in within_radius
                    if result["max_frp"] is not None
                ]

                if max_frp_values:
                    print(
                        f"  Maximum FRP among nearby events: "
                        f"{max(max_frp_values):.2f}"
                    )

        print()
        print("=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()