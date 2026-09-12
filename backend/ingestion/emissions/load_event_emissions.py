"""
Load calculated event emissions into Supabase/PostgreSQL.

Input:
    data/emissions/processed/dahej_event_emissions.csv

Database writes:
    thermal_events.emissions_estimate
    thermal_events.emissions_method

    emissions.emission_id
    emissions.event_id
    emissions.facility_id
    emissions.emissions_estimate
    emissions.method

Important:
- emissions_estimate stores GROSS CO2 in kg.
- CH4 and N2O remain in the processed CSV.
- Only agricultural_burn and wildfire events are eligible.
- Industrial_fire, gas_flare, mining_activity and mixed_or_uncertain
  are intentionally not assigned FRP-derived emissions.
"""

from __future__ import annotations

import csv
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db.database import SessionLocal


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "emissions"
    / "processed"
    / "dahej_event_emissions.csv"
)


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

ELIGIBLE_CLASSIFICATIONS = {
    "agricultural_burn",
    "wildfire",
}

EMISSIONS_METHOD = (
    "gross_CO2_kg; "
    "FRP_to_FRE_to_dry_matter; "
    "0.368_kg_dry_matter_per_MJ_FRE; "
    "IPCC_2019_Table_2.5"
)

UUID_NAMESPACE = uuid.NAMESPACE_URL


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def stable_emission_uuid(event_id: str) -> str:
    """
    Generate deterministic UUID for idempotent reruns.
    """
    return str(
        uuid.uuid5(
            UUID_NAMESPACE,
            f"phoenix-dahej-emission:{event_id}",
        )
    )


def parse_float(
    row: dict[str, Any],
    column: str,
    *,
    required: bool = True,
) -> float | None:
    """
    Parse and validate a numeric CSV field.
    """

    value = row.get(column)

    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(
                f"Missing required numeric value "
                f"in column '{column}'"
            )
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numeric value for '{column}': {value!r}"
        ) from exc

    if parsed < 0:
        raise ValueError(
            f"Negative value for '{column}': {parsed}"
        )

    return parsed


def read_emissions_csv() -> list[dict[str, Any]]:
    """
    Read and validate the processed emissions CSV.
    """

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Emissions CSV not found:\n{INPUT_CSV}"
        )

    rows: list[dict[str, Any]] = []

    with INPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                "CSV has no header."
            )

        # These are the ACTUAL column names produced
        # by calculate_event_emissions.py.
        required_columns = {
            "emission_id",
            "event_id",
            "classification",
            "landcover_class",
            "emission_factor_class",
            "observation_count",
            "fre_mj",
            "dry_matter_burned_kg",
            "co2_kg",
            "ch4_kg",
            "n2o_kg",
            "frp_to_dm_factor_kg_per_mj",
            "fre_method",
            "emission_method",
        }

        missing = (
            required_columns
            - set(reader.fieldnames)
        )

        if missing:
            raise ValueError(
                "CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(
            reader,
            start=2,
        ):

            event_id = str(
                row["event_id"]
            ).strip()

            classification = str(
                row["classification"]
            ).strip()

            if not event_id:
                raise ValueError(
                    f"Missing event_id at CSV "
                    f"line {line_number}"
                )

            if classification not in ELIGIBLE_CLASSIFICATIONS:
                raise ValueError(
                    f"Unexpected classification at "
                    f"CSV line {line_number}: "
                    f"{classification!r}"
                )

            # -----------------------------------------------------
            # Numeric validation
            # -----------------------------------------------------

            observation_count = int(
                row["observation_count"]
            )

            if observation_count < 1:
                raise ValueError(
                    f"Invalid observation_count at "
                    f"CSV line {line_number}: "
                    f"{observation_count}"
                )

            fre_mj = parse_float(
                row,
                "fre_mj",
            )

            dry_matter_burned_kg = parse_float(
                row,
                "dry_matter_burned_kg",
            )

            co2_kg = parse_float(
                row,
                "co2_kg",
            )

            ch4_kg = parse_float(
                row,
                "ch4_kg",
            )

            n2o_kg = parse_float(
                row,
                "n2o_kg",
            )

            frp_to_dm_factor = parse_float(
                row,
                "frp_to_dm_factor_kg_per_mj",
            )

            rows.append(
                {
                    "emission_id": str(
                        row["emission_id"]
                    ).strip(),

                    "event_id": event_id,

                    "classification": classification,

                    "landcover_class": str(
                        row["landcover_class"]
                    ).strip(),

                    "emission_factor_class": str(
                        row["emission_factor_class"]
                    ).strip(),

                    "observation_count": observation_count,

                    "fre_mj": fre_mj,

                    "dry_matter_burned_kg":
                        dry_matter_burned_kg,

                    "co2_kg": co2_kg,

                    "ch4_kg": ch4_kg,

                    "n2o_kg": n2o_kg,

                    "frp_to_dm_factor":
                        frp_to_dm_factor,

                    "fre_method": str(
                        row["fre_method"]
                    ).strip(),

                    "emission_method": str(
                        row["emission_method"]
                    ).strip(),
                }
            )

    return rows


# ---------------------------------------------------------------------
# Database validation
# ---------------------------------------------------------------------

def validate_event_ids(
    db,
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Confirm every CSV event exists in thermal_events.

    Returns:
        {
            event_id: {
                "facility_id": ...
            }
        }
    """

    event_ids = [
        row["event_id"]
        for row in rows
    ]

    if not event_ids:
        raise ValueError(
            "No emission rows found in CSV."
        )

    result = db.execute(
        text(
            """
            SELECT
                event_id::text AS event_id,
                facility_id::text AS facility_id
            FROM thermal_events
            WHERE event_id::text = ANY(:event_ids)
            """
        ),
        {
            "event_ids": event_ids,
        },
    )

    existing = {
        str(row.event_id): {
            "facility_id": (
                str(row.facility_id)
                if row.facility_id is not None
                else None
            )
        }
        for row in result
    }

    missing = sorted(
        set(event_ids)
        - set(existing)
    )

    if missing:
        preview = "\n".join(
            f"  - {event_id}"
            for event_id in missing[:20]
        )

        if len(missing) > 20:
            preview += (
                f"\n  ... and "
                f"{len(missing) - 20} more"
            )

        raise ValueError(
            "CSV contains event IDs that do not "
            "exist in thermal_events:\n"
            + preview
        )

    return existing


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------

def load_emissions() -> None:

    print("=" * 70)
    print("PHOENIX — LOAD EVENT EMISSIONS")
    print("=" * 70)

    print("\nInput CSV:")
    print(INPUT_CSV)

    # -------------------------------------------------------------
    # Read CSV
    # -------------------------------------------------------------

    rows = read_emissions_csv()

    print(
        f"\nCSV rows: {len(rows):,}"
    )

    # -------------------------------------------------------------
    # Duplicate event validation
    # -------------------------------------------------------------

    event_ids = [
        row["event_id"]
        for row in rows
    ]

    seen: set[str] = set()
    duplicates: set[str] = set()

    for event_id in event_ids:

        if event_id in seen:
            duplicates.add(event_id)

        seen.add(event_id)

    if duplicates:
        raise ValueError(
            "Duplicate event IDs found in emissions CSV: "
            + ", ".join(sorted(duplicates))
        )

    print(
        "Duplicate event IDs: 0"
    )

    # -------------------------------------------------------------
    # Classification validation
    # -------------------------------------------------------------

    classification_counts: dict[str, int] = {}

    for row in rows:

        classification = row["classification"]

        classification_counts[
            classification
        ] = (
            classification_counts.get(
                classification,
                0,
            )
            + 1
        )

    print("\nBy classification:")

    for classification, count in sorted(
        classification_counts.items()
    ):
        print(
            f"  {classification}: {count:,}"
        )

    unexpected = (
        set(classification_counts)
        - ELIGIBLE_CLASSIFICATIONS
    )

    if unexpected:
        raise ValueError(
            "Unexpected classifications found: "
            + ", ".join(sorted(unexpected))
        )

    # -------------------------------------------------------------
    # Database
    # -------------------------------------------------------------

    db = SessionLocal()

    try:

        print(
            "\nValidating event IDs against Supabase..."
        )

        event_info = validate_event_ids(
            db,
            rows,
        )

        print(
            f"Validated event IDs: "
            f"{len(event_info):,}"
        )

        # ---------------------------------------------------------
        # Totals
        # ---------------------------------------------------------

        total_co2 = 0.0
        total_ch4 = 0.0
        total_n2o = 0.0
        total_dry_matter = 0.0
        total_fre = 0.0

        updated_thermal_events = 0
        upserted_emissions = 0

        # ---------------------------------------------------------
        # Load each event
        # ---------------------------------------------------------

        for row in rows:

            event_id = row["event_id"]

            co2_kg = row["co2_kg"]
            ch4_kg = row["ch4_kg"]
            n2o_kg = row["n2o_kg"]
            dry_matter_burned_kg = (
                row["dry_matter_burned_kg"]
            )
            fre_mj = row["fre_mj"]

            facility_id = event_info[
                event_id
            ]["facility_id"]

            # -----------------------------------------------------
            # thermal_events
            #
            # emissions_estimate =
            # GROSS CO2 kg
            # -----------------------------------------------------

            db.execute(
                text(
                    """
                    UPDATE thermal_events
                    SET
                        emissions_estimate = :co2_kg,
                        emissions_method = :method,
                        updated_at = NOW()
                    WHERE event_id = :event_id
                    """
                ),
                {
                    "event_id": event_id,
                    "co2_kg": co2_kg,
                    "method": EMISSIONS_METHOD,
                },
            )

            updated_thermal_events += 1

            # -----------------------------------------------------
            # emissions table
            #
            # Deterministic UUID makes reruns safe.
            # -----------------------------------------------------

            emission_id = stable_emission_uuid(
                event_id
            )

            db.execute(
                text(
                    """
                    INSERT INTO emissions (
                        emission_id,
                        event_id,
                        facility_id,
                        emissions_estimate,
                        method,
                        created_at
                    )
                    VALUES (
                        :emission_id,
                        :event_id,
                        :facility_id,
                        :co2_kg,
                        :method,
                        NOW()
                    )
                    ON CONFLICT (emission_id)
                    DO UPDATE SET
                        event_id =
                            EXCLUDED.event_id,
                        facility_id =
                            EXCLUDED.facility_id,
                        emissions_estimate =
                            EXCLUDED.emissions_estimate,
                        method =
                            EXCLUDED.method
                    """
                ),
                {
                    "emission_id": emission_id,
                    "event_id": event_id,
                    "facility_id": facility_id,
                    "co2_kg": co2_kg,
                    "method": EMISSIONS_METHOD,
                },
            )

            upserted_emissions += 1

            # -----------------------------------------------------
            # Totals
            # -----------------------------------------------------

            total_co2 += co2_kg
            total_ch4 += ch4_kg
            total_n2o += n2o_kg
            total_dry_matter += (
                dry_matter_burned_kg
            )
            total_fre += fre_mj

        # ---------------------------------------------------------
        # Commit
        # ---------------------------------------------------------

        db.commit()

        print(
            "\nDatabase update committed successfully."
        )

        # ---------------------------------------------------------
        # Verification
        # ---------------------------------------------------------

        verification = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS event_count,
                    COALESCE(
                        SUM(emissions_estimate),
                        0
                    ) AS total_co2
                FROM thermal_events
                WHERE classification IN (
                    'agricultural_burn',
                    'wildfire'
                )
                AND emissions_estimate IS NOT NULL
                """
            )
        ).one()

        db_event_count = int(
            verification.event_count
        )

        db_total_co2 = float(
            verification.total_co2
        )

        print("\n" + "=" * 70)
        print("LOAD COMPLETE")
        print("=" * 70)

        print(
            f"Eligible CSV events:       "
            f"{len(rows):,}"
        )

        print(
            f"thermal_events updated:    "
            f"{updated_thermal_events:,}"
        )

        print(
            f"emissions rows upserted:   "
            f"{upserted_emissions:,}"
        )

        print("\nProcessed totals:")

        print(
            f"  FRE:                 "
            f"{total_fre:,.2f} MJ"
        )

        print(
            f"  Dry matter burned:   "
            f"{total_dry_matter:,.2f} kg"
        )

        print(
            f"  Gross CO2:           "
            f"{total_co2:,.2f} kg"
        )

        print(
            f"  CH4:                 "
            f"{total_ch4:,.2f} kg"
        )

        print(
            f"  N2O:                 "
            f"{total_n2o:,.2f} kg"
        )

        print("\nDatabase verification:")

        print(
            f"  Events with emissions: "
            f"{db_event_count:,}"
        )

        print(
            f"  Database gross CO2:     "
            f"{db_total_co2:,.2f} kg"
        )

        # ---------------------------------------------------------
        # Verification checks
        # ---------------------------------------------------------

        if db_event_count != len(rows):
            raise RuntimeError(
                "Verification failed: database event "
                "count does not match CSV row count."
            )

        tolerance = max(
            0.01,
            abs(total_co2) * 1e-9,
        )

        if abs(
            db_total_co2 - total_co2
        ) > tolerance:

            raise RuntimeError(
                "Verification failed: database CO2 "
                "total does not match CSV total."
            )

        print("\nVerification: PASS")
        print("SUCCESS")

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":

    try:

        load_emissions()

    except Exception as exc:

        print(
            "\nERROR:",
            str(exc),
            file=sys.stderr,
        )

        sys.exit(1)