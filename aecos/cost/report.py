"""CostReport model and Markdown generation for COST.md and SCHEDULE.md."""

from __future__ import annotations

import json
from typing import Any


class CostReport:
    """Complete cost and schedule report for an element."""

    def __init__(
        self,
        element_id: str = "",
        ifc_class: str = "",
        material_cost_usd: float = 0.0,
        labor_cost_usd: float = 0.0,
        total_installed_usd: float = 0.0,
        labor_hours: float = 0.0,
        duration_days: float = 0.0,
        crew_size: int = 0,
        unit_costs: dict[str, Any] | None = None,
        quantities: dict[str, float] | None = None,
        regional_factor: float = 1.0,
        region: str = "",
        source: str = "",
        predecessor_type: str = "",
    ) -> None:
        self.element_id = element_id
        self.ifc_class = ifc_class
        self.material_cost_usd = material_cost_usd
        self.labor_cost_usd = labor_cost_usd
        self.total_installed_usd = total_installed_usd
        self.labor_hours = labor_hours
        self.duration_days = duration_days
        self.crew_size = crew_size
        self.unit_costs = unit_costs or {}
        self.quantities = quantities or {}
        self.regional_factor = regional_factor
        self.region = region
        self.source = source
        self.predecessor_type = predecessor_type

    def to_markdown(self) -> str:
        """Generate COST.md content."""
        lines: list[str] = []

        lines.append(f"# Cost Report — {self.element_id or 'Unknown'}")
        lines.append("")
        lines.append(f"**IFC Class:** `{self.ifc_class}`")
        lines.append(f"**Region:** {self.region} (factor: {self.regional_factor})")
        lines.append(f"**Source:** {self.source}")
        lines.append("")

        # Quantities
        if self.quantities:
            lines.append("## Quantities")
            lines.append("")
            lines.append("| Quantity | Value |")
            lines.append("|---------|-------|")
            for key, val in self.quantities.items():
                lines.append(f"| {key} | {val} |")
            lines.append("")

        # Cost breakdown
        lines.append("## Cost Breakdown")
        lines.append("")
        lines.append("| Category | Amount (USD) |")
        lines.append("|----------|-------------|")
        lines.append(f"| Material Cost | ${self.material_cost_usd:,.2f} |")
        lines.append(f"| Labor Cost | ${self.labor_cost_usd:,.2f} |")
        lines.append(f"| **Total Installed** | **${self.total_installed_usd:,.2f}** |")
        lines.append("")

        # Unit costs
        if self.unit_costs:
            lines.append("## Unit Costs")
            lines.append("")
            for material, cost_data in self.unit_costs.items():
                if isinstance(cost_data, dict):
                    unit_type = cost_data.get("unit_type", "unit")
                    mat_cost = cost_data.get("material_cost_per_unit", 0)
                    lab_cost = cost_data.get("labor_cost_per_unit", 0)
                    lines.append(f"- **{material}:** ${mat_cost:.2f}/{unit_type} (material) + ${lab_cost:.2f}/{unit_type} (labor)")
            lines.append("")

        lines.append(f"**Labor Hours:** {self.labor_hours:.1f}")
        lines.append("")

        return "\n".join(lines)

    def to_schedule_markdown(self) -> str:
        """Generate SCHEDULE.md content."""
        lines: list[str] = []

        lines.append(f"# Schedule — {self.element_id or 'Unknown'}")
        lines.append("")
        lines.append(f"**IFC Class:** `{self.ifc_class}`")
        lines.append("")

        lines.append("## Duration")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|-----------|-------|")
        lines.append(f"| Duration | {self.duration_days:.2f} days |")
        lines.append(f"| Crew Size | {self.crew_size} |")
        lines.append(f"| Labor Hours | {self.labor_hours:.1f} |")
        lines.append(f"| Predecessor Type | {self.predecessor_type} |")
        lines.append("")

        # Quantities summary
        if self.quantities:
            lines.append("## Quantities")
            lines.append("")
            for key, val in self.quantities.items():
                lines.append(f"- {key}: {val}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Return structured JSON for audit trail."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Return dict representation."""
        return {
            "element_id": self.element_id,
            "ifc_class": self.ifc_class,
            "material_cost_usd": self.material_cost_usd,
            "labor_cost_usd": self.labor_cost_usd,
            "total_installed_usd": self.total_installed_usd,
            "labor_hours": self.labor_hours,
            "duration_days": self.duration_days,
            "crew_size": self.crew_size,
            "unit_costs": self.unit_costs,
            "quantities": self.quantities,
            "regional_factor": self.regional_factor,
            "region": self.region,
            "source": self.source,
            "predecessor_type": self.predecessor_type,
        }
