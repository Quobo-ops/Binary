"""COST.md template — placeholder structure for cost and schedule data.

Actual cost calculation is deferred to Item 10 (Cost & Schedule Hooks).
This module generates a structured placeholder.
"""

from __future__ import annotations

from typing import Any


def render_cost(
    metadata: dict[str, Any],
    materials: list[dict[str, Any]],
) -> str:
    """Return the full Markdown string for ``COST.md``."""
    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")

    lines: list[str] = []
    lines.append(f"# Cost Data — {name}")
    lines.append("")
    lines.append(f"**IFC Class:** `{ifc_class}`")
    lines.append("")

    # Material summary
    if materials:
        lines.append("## Materials")
        lines.append("")
        lines.append("| Material | Thickness |")
        lines.append("|---|---|")
        for mat in materials:
            mat_name = mat.get("name", "")
            thickness = mat.get("thickness")
            thick_str = f"{thickness}" if thickness is not None else "—"
            lines.append(f"| {mat_name} | {thick_str} |")
        lines.append("")

    # Placeholder sections
    lines.append("## Unit Cost")
    lines.append("")
    lines.append("> Awaiting cost data from Item 10 (Cost & Schedule Hooks).")
    lines.append("")
    lines.append("## Total Installed Cost")
    lines.append("")
    lines.append("> Awaiting cost data from Item 10.")
    lines.append("")
    lines.append("## Schedule")
    lines.append("")
    lines.append("> Awaiting schedule data from Item 10.")
    lines.append("")

    return "\n".join(lines)
