"""README.md template for element/template folders.

Produces a dense, scannable summary with element name, type, description,
key properties, materials, and spatial location — optimised for both human
and LLM consumption (Bible Section 3).
"""

from __future__ import annotations

from typing import Any


def render_readme(
    metadata: dict[str, Any],
    psets: dict[str, dict[str, Any]],
    materials: list[dict[str, Any]],
    spatial: dict[str, Any],
    *,
    is_template: bool = False,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Return the full Markdown string for ``README.md``."""
    name = metadata.get("Name") or metadata.get("GlobalId", "Unknown")
    ifc_class = metadata.get("IFCClass", "Unknown")
    global_id = metadata.get("GlobalId", "")
    object_type = metadata.get("ObjectType") or ""

    lines: list[str] = []

    # Title
    if is_template:
        lines.append(f"# Template: {name}")
    else:
        lines.append(f"# {name}")

    lines.append("")

    # Identity table
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| IFC Class | `{ifc_class}` |")
    lines.append(f"| GlobalId | `{global_id}` |")
    if object_type:
        lines.append(f"| Object Type | {object_type} |")
    if is_template and manifest:
        if manifest.get("version"):
            lines.append(f"| Version | {manifest['version']} |")
        if manifest.get("author"):
            lines.append(f"| Author | {manifest['author']} |")
    lines.append("")

    # Template description
    if is_template and manifest and manifest.get("description"):
        lines.append("## Description")
        lines.append("")
        lines.append(manifest["description"])
        lines.append("")

    # Key properties
    if psets:
        lines.append("## Properties")
        lines.append("")
        for pset_name, props in psets.items():
            lines.append(f"**{pset_name}**")
            lines.append("")
            for prop_name, prop_val in props.items():
                lines.append(f"- {prop_name}: `{prop_val}`")
            lines.append("")

    # Materials
    if materials:
        lines.append("## Materials")
        lines.append("")
        lines.append("| Material | Thickness | Category |")
        lines.append("|---|---|---|")
        for mat in materials:
            mat_name = mat.get("name", "")
            thickness = mat.get("thickness")
            category = mat.get("category") or ""
            thick_str = f"{thickness}" if thickness is not None else "—"
            lines.append(f"| {mat_name} | {thick_str} | {category} |")
        lines.append("")

    # Spatial location
    has_spatial = any(
        spatial.get(k)
        for k in ("site_name", "building_name", "storey_name")
    )
    if has_spatial:
        lines.append("## Spatial Location")
        lines.append("")
        if spatial.get("site_name"):
            lines.append(f"- Site: {spatial['site_name']}")
        if spatial.get("building_name"):
            lines.append(f"- Building: {spatial['building_name']}")
        if spatial.get("storey_name"):
            lines.append(f"- Storey: {spatial['storey_name']}")
        lines.append("")

    # Template tags
    if is_template and manifest and manifest.get("tags"):
        tags = manifest["tags"]
        tag_parts: list[str] = []
        for field in ("material", "region", "compliance_codes", "custom"):
            tag_parts.extend(tags.get(field, []))
        if tag_parts:
            lines.append("## Tags")
            lines.append("")
            lines.append(", ".join(f"`{t}`" for t in tag_parts))
            lines.append("")

    return "\n".join(lines)
