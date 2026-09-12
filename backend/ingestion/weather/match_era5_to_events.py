from pathlib import Path
import math
import sys

import pandas as pd
import xarray as xr
from sqlalchemy import text

from db.database import SessionLocal


# =========================================================
# Configuration
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CALM_WIND_THRESHOLD = 0.5


# =========================================================
# Calculations
# =========================================================

def calculate_wind_speed(u10, v10):
    return math.sqrt(u10 ** 2 + v10 ** 2)


def calculate_wind_direction(u10, v10):
    """
    Meteorological direction:
    direction the wind is coming FROM,
    clockwise from north.
    """
    return (
        270
        - math.degrees(
            math.atan2(v10, u10)
        )
    ) % 360


def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    R = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return (
        2
        * R
        * math.asin(
            math.sqrt(a)
        )
    )


# =========================================================
# Load events
# =========================================================

def load_events(year):

    db = SessionLocal()

    try:

        start_date = f"{year}-01-01"
        end_year = year + 1
        end_date = f"{end_year}-01-01"

        query = text(
            """
            SELECT
                event_id,
                first_seen,
                last_seen,
                latitude,
                longitude
            FROM thermal_events
            WHERE first_seen >=
                CAST(:start_date AS timestamptz)
              AND first_seen <
                CAST(:end_date AS timestamptz)
            ORDER BY first_seen
            """
        )

        rows = (
            db
            .execute(
                query,
                {
                    "start_date":
                        start_date
                        + " 00:00:00+00",

                    "end_date":
                        end_date
                        + " 00:00:00+00",
                }
            )
            .mappings()
            .all()
        )

        return pd.DataFrame(rows)

    finally:

        db.close()


# =========================================================
# Main
# =========================================================

def main():

    # -----------------------------------------------------
    # Year argument
    # -----------------------------------------------------

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "backend/ingestion/weather/"
            "match_era5_to_events.py "
            "2024"
        )

        sys.exit(1)

    year = int(sys.argv[1])

    if year not in [2023, 2024, 2025]:

        raise ValueError(
            "Year must be 2023, 2024, or 2025."
        )

    print("=" * 60)

    print(
        f"PHOENIX - ERA5 {year} "
        "EVENT WEATHER MATCHING"
    )

    print("=" * 60)

    # -----------------------------------------------------
    # Paths
    # -----------------------------------------------------

    era5_path = (
        PROJECT_ROOT
        / "data"
        / "weather"
        / f"era5_{year}"
        / "data_stream-oper_stepType-instant.nc"
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "weather"
        / "processed"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir
        / f"dahej_event_weather_{year}.csv"
    )

    # -----------------------------------------------------
    # Check file
    # -----------------------------------------------------

    if not era5_path.exists():

        raise FileNotFoundError(
            f"\nERA5 file not found:\n"
            f"{era5_path}"
        )

    print("\nERA5 file:")
    print(era5_path)

    # -----------------------------------------------------
    # Open ERA5
    # -----------------------------------------------------

    ds = xr.open_dataset(
        era5_path,
        engine="netcdf4"
    )

    print("\nERA5:")
    print(
        f"  Time points: "
        f"{ds.valid_time.size}"
    )

    print(
        f"  Latitude points: "
        f"{ds.latitude.size}"
    )

    print(
        f"  Longitude points: "
        f"{ds.longitude.size}"
    )

    # -----------------------------------------------------
    # Load events
    # -----------------------------------------------------

    events = load_events(year)

    print(
        f"\nThermal events found: "
        f"{len(events)}"
    )

    if events.empty:

        print(
            f"No {year} thermal events found."
        )

        ds.close()
        return

    # -----------------------------------------------------
    # Prepare timestamps
    # -----------------------------------------------------

    events["first_seen"] = pd.to_datetime(
        events["first_seen"],
        utc=True
    )

    era5_times = pd.to_datetime(
        ds.valid_time.values,
        utc=True
    )

    # -----------------------------------------------------
    # Match
    # -----------------------------------------------------

    results = []

    for _, event in events.iterrows():

        event_time = event["first_seen"]

        event_lat = float(
            event["latitude"]
        )

        event_lon = float(
            event["longitude"]
        )

        # -------------------------------------------------
        # Nearest time
        # -------------------------------------------------

        time_index = (
            abs(
                era5_times
                - event_time
            )
            .argmin()
        )

        weather_time = (
            era5_times[time_index]
        )

        # -------------------------------------------------
        # Nearest spatial grid point
        # -------------------------------------------------

        lat_index = (
            abs(
                ds.latitude.values
                - event_lat
            )
            .argmin()
        )

        lon_index = (
            abs(
                ds.longitude.values
                - event_lon
            )
            .argmin()
        )

        weather_lat = float(
            ds.latitude.values[
                lat_index
            ]
        )

        weather_lon = float(
            ds.longitude.values[
                lon_index
            ]
        )

        # -------------------------------------------------
        # Distance
        # -------------------------------------------------

        weather_distance_km = (
            haversine_km(
                event_lat,
                event_lon,
                weather_lat,
                weather_lon
            )
        )

        # -------------------------------------------------
        # u10 / v10
        # -------------------------------------------------

        u10 = float(
            ds["u10"]
            .isel(
                valid_time=time_index,
                latitude=lat_index,
                longitude=lon_index
            )
            .values
        )

        v10 = float(
            ds["v10"]
            .isel(
                valid_time=time_index,
                latitude=lat_index,
                longitude=lon_index
            )
            .values
        )

        # -------------------------------------------------
        # Wind calculations
        # -------------------------------------------------

        wind_speed = (
            calculate_wind_speed(
                u10,
                v10
            )
        )

        wind_direction = (
            calculate_wind_direction(
                u10,
                v10
            )
        )

        # -------------------------------------------------
        # Calm wind
        # -------------------------------------------------

        if wind_speed < CALM_WIND_THRESHOLD:

            wind_direction = None

        # -------------------------------------------------
        # Time difference
        # -------------------------------------------------

        time_difference_hours = (
            abs(
                (
                    weather_time
                    - event_time
                ).total_seconds()
            )
            / 3600
        )

        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        results.append(
            {
                "event_id":
                    str(event["event_id"]),

                "event_timestamp":
                    event_time.isoformat(),

                "event_latitude":
                    event_lat,

                "event_longitude":
                    event_lon,

                "weather_timestamp":
                    weather_time.isoformat(),

                "weather_latitude":
                    weather_lat,

                "weather_longitude":
                    weather_lon,

                "weather_distance_km":
                    weather_distance_km,

                "u10":
                    u10,

                "v10":
                    v10,

                "wind_speed":
                    wind_speed,

                "wind_direction":
                    wind_direction,

                "time_difference_hours":
                    time_difference_hours,

                "source":
                    "ERA5",
            }
        )

    # =====================================================
    # Save
    # =====================================================

    result_df = pd.DataFrame(
        results
    )

    result_df.to_csv(
        output_path,
        index=False
    )

    # =====================================================
    # Summary
    # =====================================================

    print("\n" + "=" * 60)
    print("MATCHING COMPLETE")
    print("=" * 60)

    print(
        f"\nEvents processed: "
        f"{len(result_df)}"
    )

    print(
        f"Events with weather: "
        f"{result_df['wind_speed'].notna().sum()}"
    )

    print(
        f"Events without weather: "
        f"{result_df['wind_speed'].isna().sum()}"
    )

    print(
        f"\nMaximum time difference: "
        f"{result_df['time_difference_hours'].max():.2f} hours"
    )

    print(
        f"Mean time difference: "
        f"{result_df['time_difference_hours'].mean():.2f} hours"
    )

    print(
        f"\nMaximum weather distance: "
        f"{result_df['weather_distance_km'].max():.2f} km"
    )

    print(
        f"Mean weather distance: "
        f"{result_df['weather_distance_km'].mean():.2f} km"
    )

    print(
        f"Minimum weather distance: "
        f"{result_df['weather_distance_km'].min():.2f} km"
    )

    print(
        f"\nMean wind speed: "
        f"{result_df['wind_speed'].mean():.2f} m/s"
    )

    print(
        f"Minimum wind speed: "
        f"{result_df['wind_speed'].min():.2f} m/s"
    )

    print(
        f"Maximum wind speed: "
        f"{result_df['wind_speed'].max():.2f} m/s"
    )

    print(
        f"\nCalm/near-calm events "
        f"(< {CALM_WIND_THRESHOLD} m/s): "
        f"{(result_df['wind_speed'] < CALM_WIND_THRESHOLD).sum()}"
    )

    print("\nWeather distance distribution:")

    print(
        f"  <= 5 km: "
        f"{(result_df['weather_distance_km'] <= 5).sum()}"
    )

    print(
        f"  <= 10 km: "
        f"{(result_df['weather_distance_km'] <= 10).sum()}"
    )

    print(
        f"  <= 20 km: "
        f"{(result_df['weather_distance_km'] <= 20).sum()}"
    )

    print(
        f"  > 20 km: "
        f"{(result_df['weather_distance_km'] > 20).sum()}"
    )

    print("\nOutput:")
    print(output_path)

    print("\nFirst 5 records:")

    print(
        result_df
        .head(5)
        .to_string(index=False)
    )

    ds.close()


if __name__ == "__main__":
    main()