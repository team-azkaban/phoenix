from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "emissions"
    / "processed"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "dahej_event_emission_source_2024.csv"
)


def main():
    print("=" * 70)
    print("PHOENIX - CLASSIFY EMISSION SOURCE")
    print("=" * 70)

    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

    from db.database import SessionLocal
    from db.models.thermal_event import ThermalEvent

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    db = SessionLocal()

    try:
        events = (
            db.query(ThermalEvent)
            .order_by(ThermalEvent.first_seen)
            .all()
        )

        print(f"\nThermal events found: {len(events)}")

        results = []

        for event in events:

            classification = (
                event.classification
                if event.classification
                else None
            )

            landcover = (
                event.landcover_class
                if event.landcover_class
                else None
            )

            cropland_fraction = (
                float(event.cropland_fraction)
                if event.cropland_fraction is not None
                else 0.0
            )

            forest_fraction = (
                float(event.forest_fraction)
                if event.forest_fraction is not None
                else 0.0
            )

            built_up_fraction = (
                float(event.built_up_fraction)
                if event.built_up_fraction is not None
                else 0.0
            )

            emission_source = None
            eligibility = "not_eligible"
            reason = None

            # ----------------------------------------------------------
            # Agricultural burn
            # ----------------------------------------------------------

            if classification == "agricultural_burn":
                emission_source = "agricultural_residue"
                eligibility = "eligible"
                reason = (
                    "Event classified as agricultural burn."
                )

            # ----------------------------------------------------------
            # Wildfire
            # ----------------------------------------------------------

            elif classification == "wildfire":

                # Use vegetation context to select a biomass category.
                #
                # IMPORTANT:
                # forest_fraction is a vegetation-context proxy in the
                # current PHOENIX schema, not a strict forest-only
                # fraction.

                if forest_fraction >= 0.50:
                    emission_source = "tropical_forest"
                    eligibility = "eligible"
                    reason = (
                        "Wildfire with vegetation-context "
                        "fraction >= 0.50."
                    )

                elif (
                    forest_fraction < 0.50
                    and cropland_fraction < 0.50
                ):
                    emission_source = "savanna_grassland"
                    eligibility = "eligible"
                    reason = (
                        "Wildfire with low forest-context and "
                        "low cropland fraction."
                    )

                else:
                    eligibility = "not_eligible"
                    reason = (
                        "Wildfire vegetation context is ambiguous "
                        "between cropland and non-cropland."
                    )

            # ----------------------------------------------------------
            # Gas flare
            # ----------------------------------------------------------

            elif classification == "gas_flare":
                eligibility = "not_eligible"
                reason = (
                    "Gas-flare emissions require gas flow rate, "
                    "composition or equivalent activity data."
                )

            # ----------------------------------------------------------
            # Industrial fire
            # ----------------------------------------------------------

            elif classification == "industrial_fire":
                eligibility = "not_eligible"
                reason = (
                    "Industrial-fire emissions require material/fuel "
                    "activity data not available from FIRMS FRP alone."
                )

            # ----------------------------------------------------------
            # Mining activity
            # ----------------------------------------------------------

            elif classification == "mining_activity":
                eligibility = "not_eligible"
                reason = (
                    "Mining emissions require activity/fuel data "
                    "not available from the current POC dataset."
                )

            # ----------------------------------------------------------
            # Unknown / unclassified
            # ----------------------------------------------------------

            else:
                eligibility = "not_eligible"
                reason = (
                    "No supported PHOENIX emissions classification."
                )

            results.append(
                {
                    "event_id": str(event.event_id),
                    "event_timestamp": event.first_seen,
                    "event_latitude": float(event.latitude),
                    "event_longitude": float(event.longitude),
                    "classification": classification,
                    "landcover_class": landcover,
                    "cropland_fraction": cropland_fraction,
                    "forest_fraction": forest_fraction,
                    "built_up_fraction": built_up_fraction,
                    "emission_source": emission_source,
                    "emissions_eligibility": eligibility,
                    "eligibility_reason": reason,
                }
            )

        df = pd.DataFrame(results)

        # --------------------------------------------------------------
        # Validation
        # --------------------------------------------------------------

        if df["event_id"].duplicated().any():
            raise ValueError(
                "Duplicate event IDs detected."
            )

        if len(df) != len(events):
            raise ValueError(
                "Output event count does not match database."
            )

        df.to_csv(
            OUTPUT_CSV,
            index=False,
        )

        # --------------------------------------------------------------
        # Summary
        # --------------------------------------------------------------

        print("\nEmission-source distribution:")

        print(
            df["emission_source"]
            .fillna("NONE")
            .value_counts()
            .to_string()
        )

        print("\nEligibility distribution:")

        print(
            df["emissions_eligibility"]
            .value_counts()
            .to_string()
        )

        print("\nClassification distribution:")

        print(
            df["classification"]
            .fillna("UNCLASSIFIED")
            .value_counts()
            .to_string()
        )

        print("\nOutput:")
        print(OUTPUT_CSV)

        print("\n✓ Classification CSV created.")
        print("✓ No Supabase records modified.")

    finally:
        db.close()


if __name__ == "__main__":
    main()