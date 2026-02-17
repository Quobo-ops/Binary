"""Main entry point: generate_metadata(element_folder).

Reads metadata.json, psets.json, materials.json, and spatial.json from an
Element folder and produces README.md, COMPLIANCE.md, COST.md, and USAGE.md.

Works on both raw extracted Elements and Templates (detected by the
presence of ``template_manifest.json``).  Idempotent: running twice
produces identical output.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aecos.metadata.templates.compliance import render_compliance
from aecos.metadata.templates.cost import render_cost
from aecos.metadata.templates.readme import render_readme
from aecos.metadata.templates.usage import render_usage
from aecos.metadata.writer import write_markdown

logger = logging.getLogger(__name__)

TEMPLATE_MANIFEST = "template_manifest.json"


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning an empty dict/list on failure."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.debug("Could not read %s", path, exc_info=True)
        return {}


def generate_metadata(element_folder: str | Path) -> list[Path]:
    """Generate all four Markdown files for an element or template folder.

    Parameters
    ----------
    element_folder:
        Path to an element folder (containing ``metadata.json``, etc.)
        or a template folder (additionally containing
        ``template_manifest.json``).

    Returns
    -------
    list[Path]
        Paths to the generated Markdown files.
    """
    folder = Path(element_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Element folder not found: {folder}")

    # Load source data
    metadata: dict[str, Any] = _load_json(folder / "metadata.json")
    psets: dict[str, dict[str, Any]] = _load_json(folder / "properties" / "psets.json")
    materials_raw = _load_json(folder / "materials" / "materials.json")
    materials: list[dict[str, Any]] = (
        materials_raw if isinstance(materials_raw, list) else []
    )
    spatial: dict[str, Any] = _load_json(folder / "relationships" / "spatial.json")

    # Detect template
    manifest_path = folder / TEMPLATE_MANIFEST
    is_template = manifest_path.is_file()
    manifest: dict[str, Any] | None = None
    if is_template:
        manifest = _load_json(manifest_path)

    # Render
    readme_md = render_readme(
        metadata, psets, materials, spatial,
        is_template=is_template, manifest=manifest,
    )
    compliance_md = render_compliance(
        metadata, psets, manifest=manifest,
    )
    cost_md = render_cost(metadata, materials)
    usage_md = render_usage(
        metadata, spatial,
        is_template=is_template, manifest=manifest,
    )

    # Write
    written: list[Path] = []
    written.append(write_markdown(folder, "README.md", readme_md))
    written.append(write_markdown(folder, "COMPLIANCE.md", compliance_md))
    written.append(write_markdown(folder, "COST.md", cost_md))
    written.append(write_markdown(folder, "USAGE.md", usage_md))

    logger.info("Generated metadata for %s (%d files)", folder.name, len(written))
    return written
