"""CostEngine — main entry point for cost and schedule estimation.

Usage::

    from aecos.cost import CostEngine

    engine = CostEngine()
    report = engine.estimate(element_folder)
    report = engine.estimate_from_spec(spec)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aecos.cost.estimator import calculate_quantities, quantities_from_folder
from aecos.cost.pricing import LocalProvider, PricingProvider, UnitCost
from aecos.cost.regional import get_regional_factor
from aecos.cost.report import CostReport
from aecos.cost.schedule import estimate_schedule

logger = logging.getLogger(__name__)

# Average labor rate $/hr for Louisiana 2026
_AVG_LABOR_RATE = 85.50


class CostEngine:
    """Cost and schedule estimation engine.

    Parameters
    ----------
    provider:
        Pricing provider.  Defaults to LocalProvider (embedded seed data).
    region:
        Default region code.  Defaults to 'LA' (Louisiana).
    """

    def __init__(
        self,
        provider: PricingProvider | None = None,
        region: str = "LA",
    ) -> None:
        self.provider = provider or LocalProvider()
        self.default_region = region

    def estimate(
        self,
        element_folder_or_spec: Any,
        *,
        region: str | None = None,
    ) -> CostReport:
        """Estimate cost and schedule for an element.

        Parameters
        ----------
        element_folder_or_spec:
            Path to element folder, or a ParametricSpec instance.
        region:
            Override region code.

        Returns
        -------
        CostReport
        """
        region = region or self.default_region
        regional_factor = get_regional_factor(region)

        # Determine if we have a folder path or a spec
        if isinstance(element_folder_or_spec, (str, Path)):
            return self._estimate_from_folder(
                Path(element_folder_or_spec), region, regional_factor
            )
        else:
            return self._estimate_from_spec(
                element_folder_or_spec, region, regional_factor
            )

    def _estimate_from_folder(
        self,
        folder: Path,
        region: str,
        regional_factor: float,
    ) -> CostReport:
        """Estimate from element folder."""
        ifc_class, props, quantities = quantities_from_folder(folder)

        # Load materials from folder
        mat_path = folder / "materials" / "materials.json"
        materials: list[str] = []
        if mat_path.is_file():
            try:
                mat_raw = json.loads(mat_path.read_text(encoding="utf-8"))
                if isinstance(mat_raw, list):
                    materials = [m.get("name", "") for m in mat_raw if isinstance(m, dict)]
            except (json.JSONDecodeError, OSError):
                pass

        # Load element id
        meta_path = folder / "metadata.json"
        element_id = ""
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                element_id = meta.get("GlobalId", "")
            except (json.JSONDecodeError, OSError):
                pass

        return self._calculate(
            element_id=element_id,
            ifc_class=ifc_class,
            materials=materials,
            quantities=quantities,
            region=region,
            regional_factor=regional_factor,
        )

    def _estimate_from_spec(
        self,
        spec: Any,
        region: str,
        regional_factor: float,
    ) -> CostReport:
        """Estimate from ParametricSpec."""
        ifc_class = getattr(spec, "ifc_class", "")
        properties = getattr(spec, "properties", {})
        materials = getattr(spec, "materials", [])
        name = getattr(spec, "name", "") or ""

        quantities = calculate_quantities(ifc_class, properties)

        return self._calculate(
            element_id=name,
            ifc_class=ifc_class,
            materials=materials,
            quantities=quantities,
            region=region,
            regional_factor=regional_factor,
        )

    def _calculate(
        self,
        element_id: str,
        ifc_class: str,
        materials: list[str],
        quantities: dict[str, float],
        region: str,
        regional_factor: float,
    ) -> CostReport:
        """Core calculation logic."""
        if not materials:
            materials = ["concrete"]  # default material

        primary_material = materials[0]
        unit_cost = self.provider.get_unit_cost(primary_material, ifc_class, region)

        if unit_cost is None:
            unit_cost = UnitCost(100.0, 75.0, "m2", "default estimate")

        # Calculate quantities for pricing
        quantity_value = self._get_quantity_for_unit(quantities, unit_cost.unit_type)

        # Apply regional factor
        material_cost = unit_cost.material_cost_per_unit * quantity_value * regional_factor
        labor_cost = unit_cost.labor_cost_per_unit * quantity_value * regional_factor
        total = material_cost + labor_cost

        # Labor hours (from labor cost and rate)
        labor_hours = labor_cost / _AVG_LABOR_RATE if _AVG_LABOR_RATE > 0 else 0

        # Schedule
        schedule = estimate_schedule(ifc_class, quantities)

        # Unit cost breakdown
        unit_costs: dict[str, Any] = {
            primary_material: unit_cost.to_dict(),
        }

        return CostReport(
            element_id=element_id,
            ifc_class=ifc_class,
            material_cost_usd=round(material_cost, 2),
            labor_cost_usd=round(labor_cost, 2),
            total_installed_usd=round(total, 2),
            labor_hours=round(labor_hours, 1),
            duration_days=schedule["duration_days"],
            crew_size=schedule["crew_size"],
            unit_costs=unit_costs,
            quantities=quantities,
            regional_factor=regional_factor,
            region=region,
            source=unit_cost.source,
            predecessor_type=schedule["predecessor_type"],
        )

    @staticmethod
    def _get_quantity_for_unit(quantities: dict[str, float], unit_type: str) -> float:
        """Map unit type to the appropriate quantity value."""
        mapping = {
            "m2": "area_m2",
            "m3": "volume_m3",
            "m": "length_m",
            "each": "count",
        }
        key = mapping.get(unit_type, "count")
        return quantities.get(key, 1.0)
