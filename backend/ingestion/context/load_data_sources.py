"""
Populate the PHOENIX data_sources table.

This loader is idempotent:
- Existing sources are updated.
- Missing sources are inserted.
- Safe to run multiple times.

Run from project root:

    $env:PYTHONPATH="backend"
    python backend\ingestion\context\load_data_sources.py
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from db.database import SessionLocal


# ---------------------------------------------------------------------
# Source-of-truth dataset registry
# ---------------------------------------------------------------------

DATA_SOURCES = [
    {
        "name": "NASA FIRMS VIIRS",
        "description": (
            "NASA FIRMS VIIRS thermal anomaly observations from "
            "Suomi-NPP and NOAA-20 used to construct PHOENIX "
            "thermal observations and events."
        ),
    },
    {
        "name": "ESA WorldCover 2021",
        "description": (
            "ESA WorldCover 2021 v200 10 m land-cover dataset "
            "used for event land-cover and vegetation-context "
            "enrichment."
        ),
    },
    {
        "name": "ERA5",
        "description": (
            "Copernicus/ECMWF ERA5 hourly 10 m wind components "
            "used to provide regional atmospheric wind context "
            "for thermal events."
        ),
    },
    {
        "name": "WorldPop 2024",
        "description": (
            "WorldPop 2024 constrained 100 m population dataset "
            "used to estimate population exposure within the "
            "PHOENIX event exposure radius."
        ),
    },
    {
        "name": "Government Environmental Clearance Records",
        "description": (
            "Government environmental-clearance records used "
            "to create approximate mining-context anchors for "
            "the Dahej POC."
        ),
    },
    {
        "name": "Government Flare Documentation",
        "description": (
            "Government and facility environmental documentation "
            "used to identify documented flare-system context "
            "around selected Dahej facilities."
        ),
    },
    {
        "name": "Dahej Facility Dataset",
        "description": (
            "Curated Dahej industrial facility dataset containing "
            "facility names, types, coordinates and provenance "
            "used for spatial event enrichment."
        ),
    },
    {
        "name": "IPCC 2019 Refinement",
        "description": (
            "IPCC 2019 Refinement Volume 4 default emission factors "
            "used for agricultural-burn and wildfire greenhouse-gas "
            "estimation."
        ),
    },
    {
        "name": "FRP-to-Dry-Matter POC Relationship",
        "description": (
            "Documented FRP/FRE-to-dry-matter relationship used as "
            "the PHOENIX POC intermediate step for biomass-burning "
            "emissions estimation."
        ),
    },
]


# ---------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------

def load_data_sources() -> None:

    print("=" * 70)
    print("PHOENIX — LOAD DATA SOURCES")
    print("=" * 70)

    db = SessionLocal()

    inserted = 0
    updated = 0

    try:

        for source in DATA_SOURCES:

            # ---------------------------------------------------------
            # Check whether source already exists
            # ---------------------------------------------------------

            existing = db.execute(
                text(
                    """
                    SELECT source_id
                    FROM data_sources
                    WHERE name = :name
                    """
                ),
                {
                    "name": source["name"],
                },
            ).scalar_one_or_none()

            # ---------------------------------------------------------
            # Update existing source
            # ---------------------------------------------------------

            if existing is not None:

                db.execute(
                    text(
                        """
                        UPDATE data_sources
                        SET
                            description = :description
                        WHERE name = :name
                        """
                    ),
                    {
                        "name": source["name"],
                        "description": source["description"],
                    },
                )

                updated += 1

                print(
                    f"UPDATED  {source['name']}"
                )

            # ---------------------------------------------------------
            # Insert new source
            # ---------------------------------------------------------

            else:

                db.execute(
                    text(
                        """
                        INSERT INTO data_sources (
                            name,
                            description,
                            created_at
                        )
                        VALUES (
                            :name,
                            :description,
                            NOW()
                        )
                        """
                    ),
                    {
                        "name": source["name"],
                        "description": source["description"],
                    },
                )

                inserted += 1

                print(
                    f"INSERTED {source['name']}"
                )

        # -------------------------------------------------------------
        # Commit
        # -------------------------------------------------------------

        db.commit()

        # -------------------------------------------------------------
        # Verification
        # -------------------------------------------------------------

        count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM data_sources
                """
            )
        ).scalar_one()

        print("\n" + "=" * 70)
        print("LOAD COMPLETE")
        print("=" * 70)

        print(
            f"Sources defined:  {len(DATA_SOURCES)}"
        )

        print(
            f"Inserted:         {inserted}"
        )

        print(
            f"Updated:          {updated}"
        )

        print(
            f"Database count:   {count}"
        )

        if count < len(DATA_SOURCES):
            raise RuntimeError(
                "Verification failed: not all expected "
                "data sources exist."
            )

        print("\nVerification: PASS")
        print("SUCCESS")

    except Exception as exc:

        db.rollback()

        print(
            "\nERROR:",
            str(exc),
            file=sys.stderr,
        )

        sys.exit(1)

    finally:

        db.close()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    load_data_sources()