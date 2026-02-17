"""SCHEDULE.md template — renders schedule data.

When a CostReport is available (Item 10), it is rendered inline.
Otherwise, renders a placeholder.
"""

from __future__ import annotations

from typing import Any


def render_schedule(
    metadata: dict[str, Any],
    *,
    cost_report: Any | None = None,
) -> str:
    """Return the full Markdown string for ``SCHEDULE.md``.

    Parameters
    ----------
    cost_report:
        An optional ``CostReport`` instance.  When provided, its
        ``to_schedule_markdown()`` output is used directly.
    """
    if cost_report is not None and hasattr(cost_report, "to_schedule_markdown"):
        return cost_report.to_schedule_markdown()

    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")

    lines: list[str] = []
    lines.append(f"# Schedule — {name}")
    lines.append("")
    lines.append(f"**IFC Class:** `{ifc_class}`")
    lines.append("")
    lines.append("## Duration")
    lines.append("")
    lines.append("> Awaiting schedule data from Item 10 (Cost & Schedule Hooks).")
    lines.append("")

    return "\n".join(lines)
