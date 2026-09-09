from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INDUSTRIAL_FACILITY_TYPES = {
    "power_plant",
    "chemical",
    "petrochemical",
    "copper_smelter",
    "lng_terminal",
}


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasons: list[dict[str, Any]] = field(default_factory=list)


def classify_event(
    *,
    facility_type: str | None,
    facility_distance_m: float | None,
    observation_count: int | None,
    duration_hours: float | None,
    max_frp: float | None,
    current_frp: float | None,
) -> ClassificationResult:

    reasons: list[dict[str, Any]] = []

    industrial_score = 0.0

    # ---------------------------------------------------------
    # Facility context
    # ---------------------------------------------------------

    if (
        facility_type in INDUSTRIAL_FACILITY_TYPES
        and facility_distance_m is not None
        and facility_distance_m <= 1000
    ):
        industrial_score += 0.35

        reasons.append({
            "signal": "facility_context",
            "value": facility_type,
            "weight": 0.35,
            "description": (
                "Event is within 1 km of a known "
                "industrial thermal-source facility."
            ),
        })

    elif (
        facility_type in INDUSTRIAL_FACILITY_TYPES
        and facility_distance_m is not None
        and facility_distance_m <= 2000
    ):
        industrial_score += 0.15

        reasons.append({
            "signal": "facility_context",
            "value": facility_type,
            "weight": 0.15,
            "description": (
                "Event is within 2 km of a known "
                "industrial facility."
            ),
        })

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------

    if observation_count is not None:

        if observation_count >= 5:
            industrial_score += 0.25

            reasons.append({
                "signal": "observation_count",
                "value": observation_count,
                "weight": 0.25,
                "description": (
                    "Repeated satellite detections indicate "
                    "persistent thermal activity."
                ),
            })

        elif observation_count >= 3:
            industrial_score += 0.15

            reasons.append({
                "signal": "observation_count",
                "value": observation_count,
                "weight": 0.15,
                "description": (
                    "Multiple satellite detections indicate "
                    "repeated thermal activity."
                ),
            })

        elif observation_count >= 2:
            industrial_score += 0.08

            reasons.append({
                "signal": "observation_count",
                "value": observation_count,
                "weight": 0.08,
                "description": (
                    "More than one thermal observation "
                    "is associated with the event."
                ),
            })

    # ---------------------------------------------------------
    # Duration
    # ---------------------------------------------------------

    if duration_hours is not None:

        if duration_hours >= 6:
            industrial_score += 0.20

            reasons.append({
                "signal": "duration",
                "value": duration_hours,
                "weight": 0.20,
                "description": (
                    "Long-duration thermal activity is "
                    "consistent with a persistent source."
                ),
            })

        elif duration_hours >= 2:
            industrial_score += 0.12

            reasons.append({
                "signal": "duration",
                "value": duration_hours,
                "weight": 0.12,
                "description": (
                    "Multi-hour thermal activity supports "
                    "persistent-source interpretation."
                ),
            })

        elif duration_hours > 0:
            industrial_score += 0.05

    # ---------------------------------------------------------
    # FRP
    # ---------------------------------------------------------

    frp = max_frp if max_frp is not None else current_frp

    if frp is not None:

        if frp >= 30:
            industrial_score += 0.15

            reasons.append({
                "signal": "max_frp",
                "value": frp,
                "weight": 0.15,
                "description": (
                    "High peak FRP strengthens the evidence "
                    "for a significant thermal source."
                ),
            })

        elif frp >= 10:
            industrial_score += 0.08

            reasons.append({
                "signal": "max_frp",
                "value": frp,
                "weight": 0.08,
                "description": (
                    "Elevated peak FRP provides additional "
                    "thermal-source evidence."
                ),
            })

    # ---------------------------------------------------------
    # Final decision
    # ---------------------------------------------------------

    # Strong industrial evidence.
    if industrial_score >= 0.55:
        classification = "industrial"
        confidence = min(0.95, 0.55 + industrial_score * 0.40)

    # Moderate evidence.
    elif industrial_score >= 0.35:
        classification = "industrial"
        confidence = min(0.80, 0.50 + industrial_score * 0.35)

    # Weak/insufficient evidence.
    else:
        classification = "mixed_or_uncertain"

        confidence = max(
            0.40,
            min(
                0.65,
                0.50 + industrial_score * 0.20,
            ),
        )

        reasons.append({
            "signal": "uncertainty",
            "value": industrial_score,
            "weight": 0.0,
            "description": (
                "Available POC evidence is insufficient "
                "to confidently assign a specific thermal "
                "source class."
            ),
        })

    return ClassificationResult(
        classification=classification,
        confidence=round(confidence, 3),
        reasons=reasons,
    )