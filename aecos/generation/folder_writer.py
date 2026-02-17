"""Folder writer — creates the canonical element folder structure.

Produces the exact same layout as the extraction pipeline (Item 01):

    element_<GlobalId>/
        metadata.json
        element.ifc
        properties/psets.json
        materials/materials.json
        geometry/shape.json
        relationships/spatial.json
        README.md
        COMPLIANCE.md
        COST.md
        USAGE.md
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aecos.generation.ifc_writer import write_ifc
from aecos.metadata.generator import generate_metadata

logger = logging.getLogger(__name__)


def write_element_folder(
    output_dir: Path,
    global_id: str,
    ifc_class: str,
    name: str,
    psets: dict[str, dict[str, Any]],
    materials: list[dict[str, Any]],
    geometry: dict[str, Any],
    spatial: dict[str, Any],
) -> Path:
    """Create a complete element folder and return its path.

    Parameters
    ----------
    output_dir:
        Parent directory in which to create the element folder.
    global_id:
        Unique element identifier.
    ifc_class:
        IFC class name.
    name:
        Human-readable element name.
    psets:
        Nested property-set dict.
    materials:
        List of material-layer dicts.
    geometry:
        Geometry info dict (bounding_box, volume, centroid).
    spatial:
        Spatial reference dict.

    Returns
    -------
    Path
        Path to the created element folder.
    """
    folder = output_dir / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)

    # Flatten psets for metadata.json
    flat_psets: dict[str, Any] = {}
    for pset_name, props in psets.items():
        for prop_name, prop_val in props.items():
            flat_psets[f"{pset_name}.{prop_name}"] = prop_val

    # metadata.json
    metadata = {
        "GlobalId": global_id,
        "Name": name,
        "IFCClass": ifc_class,
        "ObjectType": None,
        "Tag": None,
        "Psets": flat_psets,
    }
    (folder / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )

    # properties/psets.json
    props_dir = folder / "properties"
    props_dir.mkdir(exist_ok=True)
    (props_dir / "psets.json").write_text(
        json.dumps(psets, indent=2, default=str), encoding="utf-8"
    )

    # materials/materials.json
    mat_dir = folder / "materials"
    mat_dir.mkdir(exist_ok=True)
    (mat_dir / "materials.json").write_text(
        json.dumps(materials, indent=2, default=str), encoding="utf-8"
    )

    # geometry/shape.json
    geo_dir = folder / "geometry"
    geo_dir.mkdir(exist_ok=True)
    (geo_dir / "shape.json").write_text(
        json.dumps(geometry, indent=2, default=str), encoding="utf-8"
    )

    # relationships/spatial.json
    rel_dir = folder / "relationships"
    rel_dir.mkdir(exist_ok=True)
    (rel_dir / "spatial.json").write_text(
        json.dumps(spatial, indent=2, default=str), encoding="utf-8"
    )

    # element.ifc
    write_ifc(folder, global_id, ifc_class, name, psets, materials)

    # Generate Markdown metadata (Item 03)
    try:
        generate_metadata(folder)
    except Exception:
        logger.debug("Metadata generation failed for %s", global_id, exc_info=True)

    logger.info("Created element folder %s", folder)
    return folder
