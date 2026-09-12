"""
PHOENIX - Rule-based Thermal Event Classification

Canonical classes:
    - industrial_fire
    - gas_flare
    - agricultural_burn
    - mining_activity
    - wildfire
    - mixed_or_uncertain

POC implementation:
    Explainable rule-based classification.
    No ML model is used here.
"""

from dataclasses import dataclass
from typing import Any


# ============================================================================
# THRESHOLDS
# ============================================================================

# Documented flare contexts currently use approximate facility-level anchors.
FLARE_MAX_DISTANCE_M = 1500.0

# Mining context is intentionally kept strict because the current POC
# mining-context dataset is sparse.
MINING_MAX_DISTANCE_M = 300.0

# Industrial events within 1.5 km of a known industrial facility are
# considered strong industrial-context candidates.
INDUSTRIAL_STRONG_DISTANCE_M = 1500.0

# Broader industrial context, retained for future refinement.
INDUSTRIAL_CONTEXT_DISTANCE_M = 2000.0

# Land-cover thresholds.
AGRICULTURAL_CROPLAND_THRESHOLD = 0.50
WILDFIRE_VEGETATION_THRESHOLD = 0.50

# Generic thermal threshold.
MIN_FRP_FOR_SOURCE_CLASSIFICATION = 5.0

# Persistence thresholds.
PERSISTENT_OBSERVATIONS = 2
PERSISTENT_DURATION_HOURS = 2.0

# Agricultural burns use a stronger thermal threshold than generic events.
AGRICULTURAL_MIN_FRP = 10.0


# ============================================================================
# INDUSTRIAL FACILITY TYPES
# ============================================================================

INDUSTRIAL_FACILITY_TYPES = {
    "industrial",
    "chemical",
    "petrochemical",
    "power_plant",
    "powerplant",
    "copper_smelter",
    "gas_processing",
    "lng_terminal",
    "refinery",
    "fertilizer",
    "steel",
    "cement",
    "port",
}


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasons: list[str]


# ============================================================================
# SAFE CONVERSION HELPERS
# ============================================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to integer."""

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_facility_type(value: Any) -> str | None:
    """Normalise facility type."""

    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    return value


def _normalise_landcover_class(value: Any) -> str | None:
    """Normalise land-cover class."""

    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    return value


def _is_industrial_facility(facility_type: str | None) -> bool:
    """Return True if facility type is an industrial facility."""

    if not facility_type:
        return False

    return facility_type in INDUSTRIAL_FACILITY_TYPES


# ============================================================================
# MAIN CLASSIFIER
# ============================================================================

def classify_event(
    *,
    facility_type: str | None = None,
    landcover_class: str | None = None,
    facility_distance_m: float | None = None,
    observation_count: int | None = None,
    duration_hours: float | None = None,
    max_frp: float | None = None,
    current_frp: float | None = None,
    cropland_fraction: float | None = None,
    forest_fraction: float | None = None,
    built_up_fraction: float | None = None,
    has_flare_context: bool = False,
    has_mining_context: bool = False,
    flare_distance_m: float | None = None,
    mining_distance_m: float | None = None,
) -> ClassificationResult:
    """
    Classify a thermal event using explainable POC rules.

    Parameters
    ----------
    facility_type:
        Type of nearest known facility.

    landcover_class:
        Dominant land-cover class around the event.

        Accepted for compatibility with the service layer. The current
        classification rules primarily use the fractional land-cover
        fields below.

    facility_distance_m:
        Distance to nearest known facility.

    observation_count:
        Number of FIRMS observations belonging to the event.

    duration_hours:
        Event duration in hours.

    max_frp:
        Maximum FRP observed for the event.

    current_frp:
        Current/latest FRP.

    cropland_fraction:
        Fraction of local context classified as cropland.

    forest_fraction:
        Existing database field. In the current POC this acts as a
        broader vegetation-context proxy because the WorldCover
        enrichment aggregates vegetation classes.

    built_up_fraction:
        Fraction of local context classified as built-up.

    has_flare_context:
        Whether the event is associated with documented flare context.

    has_mining_context:
        Whether the event is associated with mining context.

    flare_distance_m:
        Distance to nearest flare context.

    mining_distance_m:
        Distance to nearest mining context.

    Returns
    -------
    ClassificationResult
        Classification, confidence and explanation reasons.
    """

    # ------------------------------------------------------------------------
    # NORMALISE INPUTS
    # ------------------------------------------------------------------------

    facility_type = _normalise_facility_type(facility_type)
    landcover_class = _normalise_landcover_class(landcover_class)

    facility_distance = (
        _safe_float(facility_distance_m)
        if facility_distance_m is not None
        else None
    )

    flare_distance = (
        _safe_float(flare_distance_m)
        if flare_distance_m is not None
        else None
    )

    mining_distance = (
        _safe_float(mining_distance_m)
        if mining_distance_m is not None
        else None
    )

    observations = _safe_int(observation_count)

    duration = _safe_float(duration_hours)

    max_frp_value = _safe_float(max_frp)

    current_frp_value = _safe_float(current_frp)

    crop = _safe_float(cropland_fraction)

    # NOTE:
    # The DB field is named forest_fraction, but the POC enrichment uses
    # it as a broader vegetation-context proxy.
    vegetation = _safe_float(forest_fraction)

    built = _safe_float(built_up_fraction)

    # ------------------------------------------------------------------------
    # GENERIC THERMAL ACTIVITY
    # ------------------------------------------------------------------------

    significant_thermal_activity = (
        max_frp_value >= MIN_FRP_FOR_SOURCE_CLASSIFICATION
        or current_frp_value >= MIN_FRP_FOR_SOURCE_CLASSIFICATION
        or observations >= PERSISTENT_OBSERVATIONS
        or duration >= PERSISTENT_DURATION_HOURS
    )

    # Agricultural classification deliberately uses a stronger rule.
    agricultural_thermal_activity = (
        max_frp_value >= AGRICULTURAL_MIN_FRP
        or observations >= 2
    )

    persistent_event = (
        observations >= PERSISTENT_OBSERVATIONS
        or duration >= PERSISTENT_DURATION_HOURS
    )

    # ------------------------------------------------------------------------
    # INDUSTRIAL CONTEXT
    # ------------------------------------------------------------------------

    industrial_context = (
        _is_industrial_facility(facility_type)
        and facility_distance is not None
        and facility_distance <= INDUSTRIAL_STRONG_DISTANCE_M
    )

    # ========================================================================
    # 1. GAS FLARE
    # ========================================================================

    # Dedicated documented flare context gets highest priority.
    flare_context = (
        has_flare_context
        and (
            flare_distance is None
            or flare_distance <= FLARE_MAX_DISTANCE_M
        )
    )

    if flare_context and significant_thermal_activity:

        reasons = [
            "Event is within documented flare context."
        ]

        if flare_distance is not None:
            reasons.append(
                f"Nearest documented flare context is "
                f"{flare_distance:.1f} m away."
            )

        if max_frp_value > 0:
            reasons.append(
                f"Maximum FRP is {max_frp_value:.2f} MW."
            )

        if observations > 0:
            reasons.append(
                f"Event contains {observations} thermal observation(s)."
            )

        if persistent_event:
            reasons.append(
                "Event shows temporal persistence."
            )

        confidence = 0.92

        if max_frp_value >= 10:
            confidence += 0.02

        if persistent_event:
            confidence += 0.02

        confidence = min(confidence, 0.97)

        return ClassificationResult(
            classification="gas_flare",
            confidence=confidence,
            reasons=reasons,
        )

    # ========================================================================
    # 2. MINING ACTIVITY
    # ========================================================================

    # Mining remains strict. We do not enlarge the radius simply to generate
    # mining classifications because the current mining-context layer is
    # sparse.
    mining_context = (
        has_mining_context
        and (
            mining_distance is None
            or mining_distance <= MINING_MAX_DISTANCE_M
        )
    )

    if mining_context and significant_thermal_activity:

        reasons = [
            "Event is within supplied mining-context radius."
        ]

        if mining_distance is not None:
            reasons.append(
                f"Nearest mining context is "
                f"{mining_distance:.1f} m away."
            )

        if max_frp_value > 0:
            reasons.append(
                f"Maximum FRP is {max_frp_value:.2f} MW."
            )

        if observations > 0:
            reasons.append(
                f"Event contains {observations} thermal observation(s)."
            )

        if persistent_event:
            reasons.append(
                "Event shows temporal persistence."
            )

        confidence = 0.90

        if persistent_event:
            confidence += 0.03

        confidence = min(confidence, 0.96)

        return ClassificationResult(
            classification="mining_activity",
            confidence=confidence,
            reasons=reasons,
        )

    # ========================================================================
    # 3. INDUSTRIAL FIRE
    # ========================================================================

    # IMPORTANT:
    #
    # Industrial context is checked BEFORE agricultural and wildfire context.
    #
    # This prevents an event near an industrial facility from being called
    # wildfire just because surrounding pixels contain vegetation.
    if industrial_context and significant_thermal_activity:

        reasons = [
            "Event is within 1.5 km of a known industrial facility.",
            f"Facility type is '{facility_type}'.",
        ]

        if facility_distance is not None:
            reasons.append(
                f"Nearest facility is "
                f"{facility_distance:.1f} m away."
            )

        if landcover_class:
            reasons.append(
                f"Dominant land-cover class is '{landcover_class}'."
            )

        if max_frp_value > 0:
            reasons.append(
                f"Maximum FRP is {max_frp_value:.2f} MW."
            )

        if observations > 0:
            reasons.append(
                f"Event contains {observations} thermal observation(s)."
            )

        if duration > 0:
            reasons.append(
                f"Event duration is {duration:.2f} hours."
            )

        if persistent_event:
            reasons.append(
                "Event shows temporal persistence."
            )

        confidence = 0.87

        # Closer facility = stronger industrial evidence.
        if facility_distance is not None:

            if facility_distance <= 1000:
                confidence += 0.03

            elif facility_distance <= 1500:
                confidence += 0.01

        # Strong FRP provides additional support.
        if max_frp_value >= 20:
            confidence += 0.02

        # Multiple observations / long duration provide support.
        if persistent_event:
            confidence += 0.02

        confidence = min(confidence, 0.95)

        return ClassificationResult(
            classification="industrial_fire",
            confidence=confidence,
            reasons=reasons,
        )

    # ========================================================================
    # 4. AGRICULTURAL BURN
    # ========================================================================

    # Requirements:
    #
    #   - >=50% cropland
    #   - <50% built-up
    #   - FRP >=10 MW OR >=2 observations
    #
    # This is intentionally stricter than generic thermal activity.
    agricultural_context = (
        crop >= AGRICULTURAL_CROPLAND_THRESHOLD
        and built < 0.50
    )

    if agricultural_context and agricultural_thermal_activity:

        reasons = [
            "Cropland dominates the local land-cover context.",
            f"Cropland fraction is {crop:.2f}.",
            f"Built-up fraction is {built:.2f}.",
        ]

        if landcover_class:
            reasons.append(
                f"Dominant land-cover class is '{landcover_class}'."
            )

        if max_frp_value >= AGRICULTURAL_MIN_FRP:
            reasons.append(
                f"Maximum FRP is {max_frp_value:.2f} MW."
            )

        if observations >= 2:
            reasons.append(
                f"Event contains {observations} thermal observations."
            )

        if duration > 0:
            reasons.append(
                f"Event duration is {duration:.2f} hours."
            )

        confidence = 0.83

        # Strong cropland dominance.
        if crop >= 0.75:
            confidence += 0.03

        # Strong thermal intensity.
        if max_frp_value >= 20:
            confidence += 0.02

        # Multiple observations.
        if observations >= 3:
            confidence += 0.02

        confidence = min(confidence, 0.94)

        return ClassificationResult(
            classification="agricultural_burn",
            confidence=confidence,
            reasons=reasons,
        )

    # ========================================================================
    # 5. WILDFIRE
    # ========================================================================

    # Requirements:
    #
    #   - >=50% vegetation-context fraction
    #   - <50% cropland
    #   - <50% built-up
    #   - NO known industrial facility within 1.5 km
    #
    # The industrial exclusion is important for avoiding false wildfire
    # classifications around industrial sites surrounded by vegetation.
    wildfire_context = (
        vegetation >= WILDFIRE_VEGETATION_THRESHOLD
        and crop < 0.50
        and built < 0.50
        and not industrial_context
    )

    if wildfire_context and significant_thermal_activity:

        reasons = [
            "Vegetation dominates the local land-cover context.",
            f"Vegetation-context fraction is {vegetation:.2f}.",
            f"Cropland fraction is {crop:.2f}.",
            f"Built-up fraction is {built:.2f}.",
            "No known industrial facility is within 1.5 km.",
        ]

        if landcover_class:
            reasons.append(
                f"Dominant land-cover class is '{landcover_class}'."
            )

        if max_frp_value > 0:
            reasons.append(
                f"Maximum FRP is {max_frp_value:.2f} MW."
            )

        if observations > 0:
            reasons.append(
                f"Event contains {observations} thermal observation(s)."
            )

        if duration > 0:
            reasons.append(
                f"Event duration is {duration:.2f} hours."
            )

        confidence = 0.84

        # Strong vegetation dominance.
        if vegetation >= 0.75:
            confidence += 0.03

        # Very low cropland.
        if crop < 0.25:
            confidence += 0.02

        # Very low built-up fraction.
        if built < 0.10:
            confidence += 0.02

        # Strong FRP.
        if max_frp_value >= 20:
            confidence += 0.02

        # Persistence.
        if persistent_event:
            confidence += 0.02

        confidence = min(confidence, 0.95)

        return ClassificationResult(
            classification="wildfire",
            confidence=confidence,
            reasons=reasons,
        )

    # ========================================================================
    # 6. MIXED / UNCERTAIN
    # ========================================================================

    reasons = [
        "Available spatial, land-cover, facility and thermal signals "
        "do not provide sufficient evidence for a specific source class."
    ]

    if landcover_class:
        reasons.append(
            f"Dominant land-cover class is '{landcover_class}'."
        )

    if max_frp_value > 0:
        reasons.append(
            f"Maximum FRP is {max_frp_value:.2f} MW."
        )

    if observations > 0:
        reasons.append(
            f"Event contains {observations} thermal observation(s)."
        )

    if facility_distance is not None:
        reasons.append(
            f"Nearest known facility is "
            f"{facility_distance:.1f} m away."
        )

    reasons.append(
        "Event remains mixed_or_uncertain rather than forcing a source label."
    )

    return ClassificationResult(
        classification="mixed_or_uncertain",
        confidence=0.50,
        reasons=reasons,
    )