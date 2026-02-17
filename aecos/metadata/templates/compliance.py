"""COMPLIANCE.md template — placeholder structure for compliance data.

Actual compliance logic is deferred to Item 07 (Code Compliance Engine).
This module generates a structured placeholder that lists applicable Psets
and notes that automated compliance checking is pending.
"""

from __future__ import annotations

from typing import Any


def render_compliance(
    metadata: dict[str, Any],
    psets: dict[str, dict[str, Any]],
    *,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Return the full Markdown string for ``COMPLIANCE.md``."""
    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")

    lines: list[str] = []
    lines.append(f"# Compliance — {name}")
    lines.append("")
    lines.append(f"**IFC Class:** `{ifc_class}`")
    lines.append("")

    # Compliance codes from manifest (if template)
    if manifest and manifest.get("tags", {}).get("compliance_codes"):
        codes = manifest["tags"]["compliance_codes"]
        lines.append("## Applicable Codes")
        lines.append("")
        for code in codes:
            lines.append(f"- {code}")
        lines.append("")

    # List property sets relevant to compliance
    lines.append("## Property Sets")
    lines.append("")
    if psets:
        for pset_name, props in psets.items():
            lines.append(f"### {pset_name}")
            lines.append("")
            for prop_name, prop_val in props.items():
                lines.append(f"- {prop_name}: `{prop_val}`")
            lines.append("")
    else:
        lines.append("No property sets extracted.")
        lines.append("")

    # Placeholder
    lines.append("## Status")
    lines.append("")
    lines.append("> Awaiting compliance engine (Item 07). Automated validation")
    lines.append("> will be added when the Code Compliance Engine is implemented.")
    lines.append("")

    return "\n".join(lines)
