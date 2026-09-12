from pathlib import Path
import sys

import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print(
            "python backend/ingestion/weather/inspect_era5.py 2024"
        )
        sys.exit(1)

    year = sys.argv[1]

    era5_path = (
        PROJECT_ROOT
        / "data"
        / "weather"
        / f"era5_{year}"
        / "data_stream-oper_stepType-instant.nc"
    )

    if not era5_path.exists():
        raise FileNotFoundError(
            f"\nERA5 file not found:\n{era5_path}"
        )

    print("=" * 60)
    print(f"PHOENIX - ERA5 {year} INSPECTION")
    print("=" * 60)

    print("\nFile:")
    print(era5_path)

    ds = xr.open_dataset(
        era5_path,
        engine="netcdf4"
    )

    print("\nDataset:")
    print(ds)

    print("\nVariables:")

    for name, var in ds.variables.items():

        print(
            f"{name} "
            f"shape={var.shape} "
            f"dtype={var.dtype} "
            f"units={var.attrs.get('units')}"
        )

    print("\nCoordinates:")

    print(
        "valid_time:",
        ds.valid_time.min().values,
        "→",
        ds.valid_time.max().values,
    )

    print(
        "latitude:",
        ds.latitude.min().values,
        "→",
        ds.latitude.max().values,
    )

    print(
        "longitude:",
        ds.longitude.min().values,
        "→",
        ds.longitude.max().values,
    )

    print("\nDimensions:")

    for dimension, size in ds.sizes.items():
        print(
            f"  {dimension}: {size}"
        )

    print("\nRequired variables:")

    for variable in ["u10", "v10"]:

        if variable in ds:
            print(
                f"  ✓ {variable}"
            )
        else:
            print(
                f"  ✗ {variable} MISSING"
            )

    ds.close()


if __name__ == "__main__":
    main()