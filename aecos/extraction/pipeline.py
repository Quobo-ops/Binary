"""Main extraction pipeline — Item 01 of the AEC OS roadmap.

Entry point: ``ifc_to_element_folders(ifc_path, output_dir)``

Parses an IFC2x3 or IFC4 file and produces a self-contained folder per
IfcBuildingElement with geometry, property, material, and relationship data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import ifcopenshell

from aecos.config import ELEMENT_BASE_CLASS
from aecos.extraction.geometry import extract_geometry, write_geometry
from aecos.extraction.materials import extract_materials, write_materials
from aecos.extraction.properties import extract_psets, flatten_psets, write_psets
from aecos.extraction.relationships import extract_spatial, write_spatial
from aecos.metadata.generator import generate_metadata
from aecos.models.element import Element

logger = logging.getLogger(__name__)


def _safe_str(value: object) -> str | None:
    """Convert an IFC attribute to a JSON-safe string, or None."""
    if value is None:
        return None
    if isinstance(value, ifcopenshell.entity_instance):
        return str(value)
    return str(value)


def _write_single_element_ifc(
    element: ifcopenshell.entity_instance,
    source_file: ifcopenshell.file,
    dest: Path,
) -> None:
    """Write a minimal IFC file containing only *element*.

    Uses ifcopenshell.api to create a fresh file, copy the element, and write
    it out.  Falls back gracefully if the copy fails (some elements reference
    complex geometry that cannot be trivially isolated).
    """
    try:
        new_ifc = ifcopenshell.file(schema=source_file.schema)
        # Create minimal project context
        ifcopenshell.api.run("root.create_entity", new_ifc, ifc_class="IfcProject")

        # Deep-copy the element into the new file
        ifcopenshell.api.run(
            "project.append_asset",
            new_ifc,
            library=source_file,
            element=element,
        )
        new_ifc.write(str(dest))
    except Exception:
        logger.debug(
            "Could not write single-element IFC for %s",
            element.GlobalId,
            exc_info=True,
        )


def _process_element(
    element: ifcopenshell.entity_instance,
    ifc_file: ifcopenshell.file,
    output_dir: Path,
) -> Element:
    """Extract all data for one element and write its folder."""
    gid = element.GlobalId

    folder = output_dir / f"element_{gid}"
    folder.mkdir(parents=True, exist_ok=True)

    # --- Extraction ---
    psets = extract_psets(element)
    geometry = extract_geometry(element, ifc_file)
    materials = extract_materials(element)
    spatial = extract_spatial(element)

    elem = Element(
        global_id=gid,
        ifc_class=element.is_a(),
        name=element.Name,
        object_type=getattr(element, "ObjectType", None),
        tag=getattr(element, "Tag", None),
        geometry=geometry,
        psets=psets,
        materials=materials,
        spatial=spatial,
    )

    # --- Write files ---

    # metadata.json
    metadata = {
        "GlobalId": elem.global_id,
        "Name": elem.name,
        "IFCClass": elem.ifc_class,
        "ObjectType": elem.object_type,
        "Tag": elem.tag,
        "Psets": flatten_psets(psets),
    }
    (folder / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )

    # element.ifc
    _write_single_element_ifc(element, ifc_file, folder / "element.ifc")

    # Sub-folder files
    write_geometry(geometry, folder)
    write_psets(psets, folder)
    write_materials(materials, folder)
    write_spatial(spatial, folder)

    # Auto-generate Markdown metadata (Item 03 integration)
    try:
        generate_metadata(folder)
    except Exception:
        logger.debug(
            "Metadata generation failed for %s", gid, exc_info=True
        )

    return elem


def ifc_to_element_folders(
    ifc_path: str | Path,
    output_dir: str | Path,
) -> list[Element]:
    """Parse an IFC file and produce one folder per building element.

    Parameters
    ----------
    ifc_path:
        Path to an IFC2x3 or IFC4 file.
    output_dir:
        Root directory under which element folders will be created.

    Returns
    -------
    list[Element]
        Pydantic models for every successfully extracted element.
    """
    ifc_path = Path(ifc_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Opening %s", ifc_path)
    ifc_file = ifcopenshell.open(str(ifc_path))

    elements: list[Element] = []
    building_elements = ifc_file.by_type(ELEMENT_BASE_CLASS)
    logger.info("Found %d building elements", len(building_elements))

    for entity in building_elements:
        try:
            elem = _process_element(entity, ifc_file, output_dir)
            elements.append(elem)
        except Exception:
            logger.warning(
                "Skipping element %s (%s) due to error",
                entity.GlobalId,
                entity.is_a(),
                exc_info=True,
            )

    logger.info(
        "Extraction complete: %d elements -> %s",
        len(elements),
        output_dir,
    )
    return elements
