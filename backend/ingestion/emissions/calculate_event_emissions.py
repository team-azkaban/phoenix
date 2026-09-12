"""
PHOENIX - POC Biomass Fire Emissions Calculation

Calculates satellite-FRP-derived biomass-burning emissions for:

    agricultural_burn
    wildfire

Industrial fires, gas flares, mining activity and mixed/uncertain events
are intentionally excluded because FRP alone does not provide the required
industrial fuel/activity data.

Method:

    FRP observations
        -> Fire Radiative Energy (FRE)
        -> Dry Matter Burned
        -> Pollutant emissions

POC assumption:

    Dry matter burned = FRE(MJ) * 0.368 kg/MJ

Emission factors:

    IPCC 2019 Refinement, Volume 4, Table 2.5

IMPORTANT:
    The 0.368 kg/MJ value is used here as a documented POC
    FRP-to-dry-matter conversion assumption.
"""


from __future__ import annotations

import csv
import math
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text

from core.config import settings
from db.database import SessionLocal


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

REFERENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "emissions"
    / "reference"
    / "emission_factors.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "emissions"
    / "processed"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "dahej_event_emissions.csv"
)


# ============================================================================
# POC PARAMETERS
# ============================================================================

# FRP -> dry matter conversion.
FRP_TO_DM_KG_PER_MJ = 0.368

# FRP is MW = MJ/s.
SECONDS_PER_HOUR = 3600.0

# Singleton events have no interval between observations.
# We therefore assign one hour of representative activity.
SINGLETON_DURATION_HOURS = 1.0

# Maximum interval used when integrating between observations.
MAX_INTEGRATION_GAP_HOURS = 24.0


# ============================================================================
# DEFAULT IPCC EMISSION FACTORS
# ============================================================================
#
# Units:
#     g pollutant / kg dry matter
#
# These values correspond to the project's reference CSV.
# ============================================================================

DEFAULT_FACTORS = {

    "agricultural_residue": {
        "CO2": 1515.0,
        "CH4": 2.7,
        "N2O": 0.07,
    },

    "savanna_grassland": {
        "CO2": 1613.0,
        "CH4": 2.3,
        "N2O": 0.21,
    },

    "tropical_forest": {
        "CO2": 1580.0,
        "CH4": 6.8,
        "N2O": 0.20,
    },

    "extra_tropical_forest": {
        "CO2": 1569.0,
        "CH4": 4.7,
        "N2O": 0.26,
    },
}


# ============================================================================
# HELPERS
# ============================================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert a value to float."""

    if value is None:
        return default

    try:
        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """Safely convert a value to integer."""

    if value is None:
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


# ============================================================================
# EMISSION FACTOR CATEGORY
# ============================================================================

def classify_emission_factor_class(
    classification: str | None,
    landcover_class: str | None,
    cropland_fraction: float,
    vegetation_fraction: float,
) -> str | None:
    """
    Select the appropriate biomass emission-factor category.

    agricultural_burn
        -> agricultural_residue

    wildfire + tree_cover/mangroves
        -> tropical_forest

    wildfire + grassland/shrubland/moss
        -> savanna_grassland

    other wildfire with strong vegetation
        -> extra_tropical_forest

    Other classifications
        -> None
    """

    if classification == "agricultural_burn":
        return "agricultural_residue"

    if classification != "wildfire":
        return None

    landcover = (
        str(landcover_class).strip().lower()
        if landcover_class
        else ""
    )

    if landcover in {
        "tree_cover",
        "mangroves",
    }:
        return "tropical_forest"

    if landcover in {
        "grassland",
        "shrubland",
        "moss_lichen",
    }:
        return "savanna_grassland"

    if vegetation_fraction >= 0.50:
        return "extra_tropical_forest"

    return None


# ============================================================================
# LOAD EMISSION FACTORS
# ============================================================================

def load_emission_factors() -> dict[str, dict[str, float]]:
    """
    Load emission factors from the project's CSV.

    Falls back to DEFAULT_FACTORS when the CSV is missing or incomplete.
    """

    factors: dict[str, dict[str, float]] = {}

    if REFERENCE_FILE.exists():

        with REFERENCE_FILE.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                source_class = (
                    row.get("source_class") or ""
                ).strip()

                pollutant = (
                    row.get("pollutant") or ""
                ).strip()

                if not source_class or not pollutant:
                    continue

                factor = safe_float(
                    row.get("emission_factor"),
                    default=-1.0,
                )

                if factor < 0:
                    continue

                factors.setdefault(
                    source_class,
                    {},
                )[pollutant] = factor

    # Fill any missing categories/pollutants from defaults.
    for source_class, default_values in DEFAULT_FACTORS.items():

        if source_class not in factors:
            factors[source_class] = {}

        for pollutant, value in default_values.items():

            if pollutant not in factors[source_class]:
                factors[source_class][pollutant] = value

    return factors


# ============================================================================
# FRE CALCULATION
# ============================================================================

def calculate_fre_mj(
    observations: list[tuple[Any, float]],
) -> tuple[float, str]:
    """
    Calculate Fire Radiative Energy (FRE) in MJ.

    Multiple observations:
        trapezoidal integration of FRP over time.

    Singleton observation:
        one-hour representative activity assumption.

    Returns:
        FRE in MJ
        calculation method
    """

    if not observations:
        return 0.0, "no_observations"

    # Sort chronologically.
    observations = sorted(
        observations,
        key=lambda item: item[0],
    )

    # ------------------------------------------------------------------------
    # SINGLETON
    # ------------------------------------------------------------------------

    if len(observations) == 1:

        _, frp = observations[0]

        frp = max(
            safe_float(frp),
            0.0,
        )

        fre_mj = (
            frp
            * SECONDS_PER_HOUR
            * SINGLETON_DURATION_HOURS
        )

        return (
            fre_mj,
            "singleton_frp_1h_assumption",
        )

    # ------------------------------------------------------------------------
    # MULTIPLE OBSERVATIONS
    # ------------------------------------------------------------------------

    # IMPORTANT:
    # Initialize this before the loop.
    #
    # This fixes the UnboundLocalError that occurred in the previous version.
    fre_mj = 0.0

    for index in range(
        len(observations) - 1
    ):

        timestamp_a, frp_a = observations[index]

        timestamp_b, frp_b = observations[index + 1]

        # Calculate elapsed seconds.
        try:

            delta_seconds = (
                timestamp_b - timestamp_a
            ).total_seconds()

        except AttributeError:

            continue

        # Ignore invalid intervals.
        if delta_seconds <= 0:
            continue

        # Prevent extremely large gaps from creating unrealistic inferred
        # fire energy.
        delta_seconds = min(
            delta_seconds,
            MAX_INTEGRATION_GAP_HOURS * 3600.0,
        )

        frp_a = max(
            safe_float(frp_a),
            0.0,
        )

        frp_b = max(
            safe_float(frp_b),
            0.0,
        )

        # Trapezoidal average FRP.
        mean_frp = (
            frp_a + frp_b
        ) / 2.0

        # MW = MJ/s.
        fre_mj += (
            mean_frp
            * delta_seconds
        )

    # ------------------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------------------

    # If timestamps were unusable or all intervals were invalid,
    # use the first observation with the singleton assumption.
    if fre_mj <= 0:

        _, frp = observations[0]

        frp = max(
            safe_float(frp),
            0.0,
        )

        fre_mj = (
            frp
            * SECONDS_PER_HOUR
            * SINGLETON_DURATION_HOURS
        )

        return (
            fre_mj,
            "fallback_frp_1h_assumption",
        )

    return (
        fre_mj,
        "trapezoidal_observation_integration",
    )


# ============================================================================
# POLLUTANT CALCULATION
# ============================================================================

def calculate_pollutant_mass(
    dry_matter_kg: float,
    emission_factor_g_per_kg: float,
) -> float:
    """
    Convert dry matter burned to pollutant mass in kg.

    emission_factor:
        grams pollutant / kg dry matter
    """

    grams = (
        dry_matter_kg
        * emission_factor_g_per_kg
    )

    return grams / 1000.0


# ============================================================================
# LOAD EVENTS
# ============================================================================

def load_eligible_events(
    db,
) -> list[dict[str, Any]]:
    """
    Load events eligible for biomass-burning emissions estimation.
    """

    query = text(
        """
        SELECT
            te.event_id,
            te.first_seen,
            te.last_seen,
            te.latitude,
            te.longitude,
            te.observation_count,
            te.duration,
            te.current_frp,
            te.max_frp,
            te.mean_frp,
            te.classification,
            te.landcover_class,
            te.cropland_fraction,
            te.forest_fraction,
            te.built_up_fraction
        FROM thermal_events te
        WHERE te.classification IN (
            'agricultural_burn',
            'wildfire'
        )
        ORDER BY
            te.first_seen,
            te.event_id
        """
    )

    rows = db.execute(query).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================================
# LOAD EVENT OBSERVATIONS
# ============================================================================

def load_event_observations(
    db,
    event_id: str,
) -> list[tuple[Any, float]]:
    """
    Load underlying thermal observations belonging to an event.
    """

    query = text(
        """
        SELECT
            o.timestamp,
            o.frp
        FROM event_observations eo
        JOIN thermal_observations o
          ON o.observation_id = eo.observation_id
        WHERE
            eo.event_id = :event_id
            AND o.frp IS NOT NULL
            AND o.frp >= 0
        ORDER BY
            o.timestamp
        """
    )

    rows = db.execute(
        query,
        {
            "event_id": event_id,
        },
    ).all()

    return [
        (
            row[0],
            safe_float(row[1]),
        )
        for row in rows
    ]


# ============================================================================
# MAIN CALCULATION
# ============================================================================

def calculate_all_events() -> Path:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    factors = load_emission_factors()

    db = SessionLocal()

    try:

        events = load_eligible_events(db)

        print(
            f"Eligible biomass events: {len(events):,}"
        )

        output_rows: list[dict[str, Any]] = []

        processed = 0
        skipped = 0

        # --------------------------------------------------------------------
        # PROCESS EVENTS
        # --------------------------------------------------------------------

        for event in events:

            event_id = str(
                event["event_id"]
            )

            classification = event.get(
                "classification"
            )

            landcover_class = event.get(
                "landcover_class"
            )

            cropland_fraction = safe_float(
                event.get(
                    "cropland_fraction"
                )
            )

            vegetation_fraction = safe_float(
                event.get(
                    "forest_fraction"
                )
            )

            # Determine emission-factor category.
            factor_class = classify_emission_factor_class(
                classification=classification,
                landcover_class=landcover_class,
                cropland_fraction=cropland_fraction,
                vegetation_fraction=vegetation_fraction,
            )

            if factor_class is None:

                skipped += 1

                continue

            # Load underlying observations.
            observations = load_event_observations(
                db,
                event_id,
            )

            if not observations:

                skipped += 1

                continue

            # Calculate FRE.
            fre_mj, fre_method = calculate_fre_mj(
                observations
            )

            if fre_mj <= 0:

                skipped += 1

                continue

            # ----------------------------------------------------------------
            # DRY MATTER
            # ----------------------------------------------------------------

            dry_matter_kg = (
                fre_mj
                * FRP_TO_DM_KG_PER_MJ
            )

            # ----------------------------------------------------------------
            # EMISSION FACTORS
            # ----------------------------------------------------------------

            source_factors = factors.get(
                factor_class,
                {},
            )

            co2_factor = source_factors.get(
                "CO2",
                0.0,
            )

            ch4_factor = source_factors.get(
                "CH4",
                0.0,
            )

            n2o_factor = source_factors.get(
                "N2O",
                0.0,
            )

            # ----------------------------------------------------------------
            # POLLUTANT MASSES
            # ----------------------------------------------------------------

            co2_kg = calculate_pollutant_mass(
                dry_matter_kg,
                co2_factor,
            )

            ch4_kg = calculate_pollutant_mass(
                dry_matter_kg,
                ch4_factor,
            )

            n2o_kg = calculate_pollutant_mass(
                dry_matter_kg,
                n2o_factor,
            )

            # ----------------------------------------------------------------
            # OUTPUT ROW
            # ----------------------------------------------------------------

            emission_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"phoenix-emissions:{event_id}",
                )
            )

            output_rows.append(
                {
                    "emission_id": emission_id,

                    "event_id": event_id,

                    "classification": classification,

                    "landcover_class": landcover_class,

                    "emission_factor_class": factor_class,

                    "observation_count": len(
                        observations
                    ),

                    "fre_mj": fre_mj,

                    "dry_matter_burned_kg": (
                        dry_matter_kg
                    ),

                    "co2_kg": co2_kg,

                    "ch4_kg": ch4_kg,

                    "n2o_kg": n2o_kg,

                    "frp_to_dm_factor_kg_per_mj": (
                        FRP_TO_DM_KG_PER_MJ
                    ),

                    "fre_method": fre_method,

                    "emission_method": (
                        "FRP_to_FRE_to_dry_matter"
                        "_then_IPCC_2019_factors"
                    ),
                }
            )

            processed += 1

            if processed % 100 == 0:

                print(
                    f"  Calculated "
                    f"{processed:,} events"
                )

        # --------------------------------------------------------------------
        # WRITE CSV
        # --------------------------------------------------------------------

        fieldnames = [
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
        ]

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(
                output_rows
            )

        # --------------------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------------------

        print()
        print(
            "Emission calculation complete."
        )

        print(
            f"  Eligible events:   {len(events):,}"
        )

        print(
            f"  Calculated events: {len(output_rows):,}"
        )

        print(
            f"  Skipped events:    {skipped:,}"
        )

        print()
        print(
            f"Output: {OUTPUT_FILE}"
        )

        # --------------------------------------------------------------------
        # CLASS SUMMARY
        # --------------------------------------------------------------------

        by_class: dict[str, int] = {}

        for row in output_rows:

            classification = row[
                "classification"
            ]

            by_class[classification] = (
                by_class.get(
                    classification,
                    0,
                )
                + 1
            )

        print()
        print("By classification:")

        for classification, count in sorted(
            by_class.items()
        ):

            print(
                f"  {classification:<24}"
                f" {count:,}"
            )

        # --------------------------------------------------------------------
        # FACTOR SUMMARY
        # --------------------------------------------------------------------

        by_factor: dict[str, int] = {}

        for row in output_rows:

            factor_class = row[
                "emission_factor_class"
            ]

            by_factor[factor_class] = (
                by_factor.get(
                    factor_class,
                    0,
                )
                + 1
            )

        print()
        print("By emission-factor category:")

        for factor_class, count in sorted(
            by_factor.items()
        ):

            print(
                f"  {factor_class:<24}"
                f" {count:,}"
            )

        # --------------------------------------------------------------------
        # TOTALS
        # --------------------------------------------------------------------

        total_co2 = sum(
            safe_float(row["co2_kg"])
            for row in output_rows
        )

        total_ch4 = sum(
            safe_float(row["ch4_kg"])
            for row in output_rows
        )

        total_n2o = sum(
            safe_float(row["n2o_kg"])
            for row in output_rows
        )

        total_dm = sum(
            safe_float(
                row["dry_matter_burned_kg"]
            )
            for row in output_rows
        )

        total_fre = sum(
            safe_float(row["fre_mj"])
            for row in output_rows
        )

        print()
        print("Overall totals:")
        print(
            f"  FRE:                  "
            f"{total_fre:,.2f} MJ"
        )
        print(
            f"  Dry matter burned:    "
            f"{total_dm:,.2f} kg"
        )
        print(
            f"  Gross CO2:            "
            f"{total_co2:,.2f} kg"
        )
        print(
            f"  CH4:                  "
            f"{total_ch4:,.2f} kg"
        )
        print(
            f"  N2O:                  "
            f"{total_n2o:,.2f} kg"
        )

        return OUTPUT_FILE

    finally:

        db.close()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    try:

        output = calculate_all_events()

        print()
        print("SUCCESS")
        print(output)

    except Exception as exc:

        print()
        print("ERROR")
        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise