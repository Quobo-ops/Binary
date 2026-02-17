"""USAGE.md template — how to use this element or template.

Provides insertion notes and usage guidance.
"""

from __future__ import annotations

from typing import Any


def render_usage(
    metadata: dict[str, Any],
    spatial: dict[str, Any],
    *,
    is_template: bool = False,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Return the full Markdown string for ``USAGE.md``."""
    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")
    global_id = metadata.get("GlobalId", "")

    lines: list[str] = []

    if is_template:
        lines.append(f"# Usage — Template: {name}")
    else:
        lines.append(f"# Usage — {name}")
    lines.append("")

    lines.append(f"**IFC Class:** `{ifc_class}`")
    lines.append("")

    # Insertion notes
    lines.append("## Insertion")
    lines.append("")
    if is_template:
        lines.append("This template can be inserted into a project via the AEC OS API:")
        lines.append("")
        lines.append("```python")
        lines.append("from aecos.templates import TemplateLibrary")
        lines.append("")
        lines.append(f'library = TemplateLibrary("path/to/library")')
        lines.append(f'folder = library.get_template("{global_id}")')
        lines.append("```")
    else:
        lines.append("This element was extracted from an IFC file. To promote it")
        lines.append("to a reusable template:")
        lines.append("")
        lines.append("```python")
        lines.append("from aecos.templates import TemplateLibrary")
        lines.append("")
        lines.append(f'library = TemplateLibrary("path/to/library")')
        lines.append(f'library.promote_to_template("path/to/element_{global_id}")')
        lines.append("```")
    lines.append("")

    # Spatial context
    has_spatial = any(
        spatial.get(k)
        for k in ("site_name", "building_name", "storey_name")
    )
    if has_spatial:
        lines.append("## Original Location")
        lines.append("")
        parts: list[str] = []
        if spatial.get("site_name"):
            parts.append(spatial["site_name"])
        if spatial.get("building_name"):
            parts.append(spatial["building_name"])
        if spatial.get("storey_name"):
            parts.append(spatial["storey_name"])
        lines.append(" > ".join(parts))
        lines.append("")

    # Template-specific notes
    if is_template and manifest:
        if manifest.get("tags", {}).get("region"):
            regions = manifest["tags"]["region"]
            lines.append("## Region")
            lines.append("")
            lines.append(", ".join(regions))
            lines.append("")

    # Notes
    lines.append("## Notes")
    lines.append("")
    lines.append("- Validate compliance before inserting into production models")
    lines.append("- Check spatial coordination and clash detection after placement")
    lines.append("")

    return "\n".join(lines)
