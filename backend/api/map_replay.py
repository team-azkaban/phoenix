from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/map/replay",
    tags=["map-replay"],
)


# ------------------------------------------------------------------
# POC DATA WINDOWS
#
# These are INTERNAL ONLY.
#
# The frontend never receives these dates.
# The frontend only receives generic window IDs.
# ------------------------------------------------------------------

REPLAY_SCENARIOS = [
    {
        "id": "window-1",
        "label": "High-intensity activity",

        "data_start": datetime(
            2025, 4, 21,
            tzinfo=timezone.utc,
        ),
        "data_end": datetime(
            2025, 4, 28,
            tzinfo=timezone.utc,
        ),
    },

    {
        "id": "window-2",
        "label": "High-risk activity",

        "data_start": datetime(
            2024, 3, 5,
            tzinfo=timezone.utc,
        ),
        "data_end": datetime(
            2024, 3, 12,
            tzinfo=timezone.utc,
        ),
    },

    {
        "id": "window-3",
        "label": "High activity period",

        "data_start": datetime(
            2023, 4, 6,
            tzinfo=timezone.utc,
        ),
        "data_end": datetime(
            2023, 4, 13,
            tzinfo=timezone.utc,
        ),
    },

    {
        "id": "window-4",
        "label": "Dense activity",

        "data_start": datetime(
            2024, 1, 23,
            tzinfo=timezone.utc,
        ),
        "data_end": datetime(
            2024, 1, 30,
            tzinfo=timezone.utc,
        ),
    },
]


def get_scenario(scenario_id: str):
    for scenario in REPLAY_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario

    raise HTTPException(
        status_code=404,
        detail="Window not found.",
    )


@router.get("")
def get_replay_windows():
    """
    UI-facing endpoint.

    IMPORTANT:
    Historical dates are deliberately not returned.
    """

    return {
        "region": "dahej",

        "windows": [
            {
                "id": scenario["id"],
                "label": scenario["label"],
            }
            for scenario in REPLAY_SCENARIOS
        ],
    }