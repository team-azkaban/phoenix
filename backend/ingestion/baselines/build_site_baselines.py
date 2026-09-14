"""
Build and load PHOENIX site baselines.

Source:
    thermal_events

Target:
    site_baselines

One baseline is created for every facility that has at least one
facility-linked thermal event.

Baseline fields:
    baseline_frp
    frp_std
    typical_active_hours
    typical_duration
    seasonal_pattern
    historical_event_count

The calculation uses the historical thermal_events already stored
in Supabase.

Run from project root:

    $env:PYTHONPATH="backend"
    python backend\ingestion\baselines\build_site_baselines.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from db.database import SessionLocal
from services.facility_intelligence import upsert_baselines


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------

def load_baselines() -> None:
    print("=" * 70)
    print("PHOENIX - BUILD SITE BASELINES")
    print("=" * 70)

    db = SessionLocal()
    try:
        summary = upsert_baselines(db)
        print(f"Facilities processed: {summary['facilities_processed']:,}")
        print(f"Events used:          {summary['events_used']:,}")
        print("Baseline rows upserted successfully.")
    finally:
        db.close()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    load_baselines()