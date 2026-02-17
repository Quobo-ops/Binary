"""Regional adjustment factors by location."""

from __future__ import annotations

from aecos.cost.seed_data import REGIONAL_FACTORS

# Default region (Baton Rouge / Louisiana)
DEFAULT_REGION = "LA"


def get_regional_factor(region: str | None = None) -> float:
    """Return the regional cost adjustment factor.

    Parameters
    ----------
    region:
        Region code (e.g. 'LA', 'CA', 'NY').  Defaults to Louisiana.

    Returns a multiplier (1.0 = US average).
    """
    if region is None:
        region = DEFAULT_REGION
    return REGIONAL_FACTORS.get(region.upper(), 1.0)


def list_regions() -> dict[str, float]:
    """Return all available region codes and their factors."""
    return dict(REGIONAL_FACTORS)
