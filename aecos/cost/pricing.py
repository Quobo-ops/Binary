"""PricingProvider interface and local seed-data provider.

No external CSV files or API calls required — all pricing is embedded.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

from aecos.cost.seed_data import DEFAULT_PRICING, SEED_PRICING

logger = logging.getLogger(__name__)


class UnitCost:
    """Unit cost breakdown for a material/element combination."""

    def __init__(
        self,
        material_cost_per_unit: float,
        labor_cost_per_unit: float,
        unit_type: str,
        source: str = "",
    ) -> None:
        self.material_cost_per_unit = material_cost_per_unit
        self.labor_cost_per_unit = labor_cost_per_unit
        self.unit_type = unit_type
        self.source = source

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_cost_per_unit": self.material_cost_per_unit,
            "labor_cost_per_unit": self.labor_cost_per_unit,
            "unit_type": self.unit_type,
            "source": self.source,
        }


class PricingProvider(abc.ABC):
    """Abstract pricing provider."""

    @abc.abstractmethod
    def get_unit_cost(
        self,
        material: str,
        ifc_class: str,
        region: str = "US_AVG",
    ) -> UnitCost | None:
        """Return unit cost for material/class/region, or None if not found."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is ready."""


class LocalProvider(PricingProvider):
    """Pricing from embedded seed data.  Always available."""

    def get_unit_cost(
        self,
        material: str,
        ifc_class: str,
        region: str = "US_AVG",
    ) -> UnitCost:
        """Look up unit cost from seed data.

        Falls back to default pricing if the specific combination is
        not found.
        """
        key = (material.lower(), ifc_class)
        data = SEED_PRICING.get(key)

        if data is None:
            # Try without case sensitivity on IFC class
            for (mat, cls), d in SEED_PRICING.items():
                if mat == material.lower() and cls.lower() == ifc_class.lower():
                    data = d
                    break

        if data is None:
            # Try just material match
            for (mat, cls), d in SEED_PRICING.items():
                if mat == material.lower():
                    data = d
                    break

        if data is None:
            data = DEFAULT_PRICING

        return UnitCost(
            material_cost_per_unit=data["material_cost_per_unit"],
            labor_cost_per_unit=data["labor_cost_per_unit"],
            unit_type=data["unit_type"],
            source=data.get("source", ""),
        )

    def is_available(self) -> bool:
        return True
