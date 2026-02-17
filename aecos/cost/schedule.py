"""ScheduleEstimator — duration from element type and quantity."""

from __future__ import annotations

from typing import Any

from aecos.cost.seed_data import PRODUCTIVITY_RATES


def estimate_schedule(
    ifc_class: str,
    quantities: dict[str, float],
) -> dict[str, Any]:
    """Estimate construction duration for an element.

    Returns dict with: duration_days, crew_size, predecessor_type.
    """
    rates = PRODUCTIVITY_RATES.get(ifc_class, {})

    if not rates:
        return {
            "duration_days": 1.0,
            "crew_size": 2,
            "predecessor_type": "general",
        }

    crew_size = rates.get("crew_size", 2)
    predecessor_type = rates.get("predecessor_type", "general")

    # Calculate duration based on the appropriate quantity unit
    duration = 0.0

    if "rate_per_m2" in rates and "area_m2" in quantities:
        duration = quantities["area_m2"] * rates["rate_per_m2"]
    elif "rate_per_m3" in rates and "volume_m3" in quantities:
        duration = quantities["volume_m3"] * rates["rate_per_m3"]
    elif "rate_per_m" in rates and "length_m" in quantities:
        duration = quantities["length_m"] * rates["rate_per_m"]
    elif "rate_per_each" in rates and "count" in quantities:
        duration = quantities["count"] * rates["rate_per_each"]
    elif "rate_per_each" in rates:
        duration = rates["rate_per_each"]
    else:
        duration = 1.0

    # Minimum duration is 0.1 days
    duration = max(0.1, round(duration, 2))

    return {
        "duration_days": duration,
        "crew_size": crew_size,
        "predecessor_type": predecessor_type,
    }
