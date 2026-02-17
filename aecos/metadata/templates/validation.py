"""VALIDATION.md template — renders validation data.

When a ValidationReport is available (Item 09), it is rendered inline.
Otherwise, renders a placeholder.
"""

from __future__ import annotations

from typing import Any


def render_validation(
    metadata: dict[str, Any],
    *,
    validation_report: Any | None = None,
) -> str:
    """Return the full Markdown string for ``VALIDATION.md``.

    Parameters
    ----------
    validation_report:
        An optional ``ValidationReport`` instance.  When provided, its
        ``to_markdown()`` output is used directly.
    """
    if validation_report is not None and hasattr(validation_report, "to_markdown"):
        return validation_report.to_markdown()

    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")

    lines: list[str] = []
    lines.append(f"# Validation — {name}")
    lines.append("")
    lines.append(f"**IFC Class:** `{ifc_class}`")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("> Awaiting validation engine (Item 09). Automated validation")
    lines.append("> will be added when the Clash & Validation Suite is run.")
    lines.append("")

    return "\n".join(lines)
