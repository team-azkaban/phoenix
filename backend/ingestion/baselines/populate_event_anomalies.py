"""Classify thermal events against facility-specific behavioral baselines."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from db.database import SessionLocal
from services.facility_intelligence import classify_events


def main() -> None:
    print("=" * 70)
    print("PHOENIX - CLASSIFY EVENT ANOMALIES")
    print("=" * 70)

    db = SessionLocal()
    try:
        summary = classify_events(db)
        for state in ("ROUTINE", "PERSISTENT", "ANOMALOUS", "UNKNOWN"):
            print(f"{state:10}: {summary.get(state, 0):,}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
