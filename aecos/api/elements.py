"""Element-level CRUD operations.

Create, read, update, delete, and list elements within an AEC OS
project.  Each element lives in its own folder following the Item 01
extraction format.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from aecos.metadata.generator import generate_metadata
from aecos.models.element import Element, GeometryInfo, MaterialLayer, SpatialReference

logger = logging.getLogger(__name__)


def _elements_dir(project_root: Path) -> Path:
    """Return the elements directory for a project."""
    return project_root / "elements"


def create_element(
    project_root: Path,
    ifc_class: str,
    *,
    name: str | None = None,
    properties: dict[str, dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
    global_id: str | None = None,
) -> Element:
    """Create a new element folder from scratch.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    ifc_class:
        IFC class name (e.g. ``IfcWall``, ``IfcDoor``).
    name:
        Human-readable element name.
    properties:
        Property sets as nested dict ``{pset_name: {prop: value}}``.
    materials:
        List of material dicts ``[{name, thickness, category, fraction}]``.
    global_id:
        Explicit GlobalId.  Auto-generated if *None*.

    Returns the created :class:`Element` model.
    """
    if global_id is None:
        global_id = uuid.uuid4().hex[:22].upper()

    if name is None:
        name = f"{ifc_class}_{global_id[:8]}"

    properties = properties or {}
    materials = materials or []

    elem_dir = _elements_dir(project_root)
    folder = elem_dir / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)

    # Build Element model
    mat_layers = [MaterialLayer(**m) for m in materials]
    elem = Element(
        global_id=global_id,
        ifc_class=ifc_class,
        name=name,
        psets=properties,
        materials=mat_layers,
    )

    # Flatten psets for metadata.json
    flat_psets: dict[str, Any] = {}
    for pset_name, props in properties.items():
        for prop_name, prop_val in props.items():
            flat_psets[f"{pset_name}.{prop_name}"] = prop_val

    # Write metadata.json
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

    # Write sub-folder files
    props_dir = folder / "properties"
    props_dir.mkdir(exist_ok=True)
    (props_dir / "psets.json").write_text(
        json.dumps(properties, indent=2, default=str), encoding="utf-8"
    )

    mat_dir = folder / "materials"
    mat_dir.mkdir(exist_ok=True)
    (mat_dir / "materials.json").write_text(
        json.dumps([m.model_dump(mode="json") for m in mat_layers], indent=2),
        encoding="utf-8",
    )

    geo_dir = folder / "geometry"
    geo_dir.mkdir(exist_ok=True)
    (geo_dir / "shape.json").write_text(
        json.dumps(elem.geometry.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    rel_dir = folder / "relationships"
    rel_dir.mkdir(exist_ok=True)
    (rel_dir / "spatial.json").write_text(
        json.dumps(elem.spatial.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    # Generate Markdown metadata (Item 03)
    try:
        generate_metadata(folder)
    except Exception:
        logger.debug("Metadata generation failed for %s", global_id, exc_info=True)

    logger.info("Created element %s (%s) at %s", name, ifc_class, folder)
    return elem


def get_element(project_root: Path, element_id: str) -> Element | None:
    """Load an Element model from its folder.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    element_id:
        The GlobalId of the element.

    Returns the :class:`Element` or *None* if not found.
    """
    folder = _elements_dir(project_root) / f"element_{element_id}"
    if not folder.is_dir():
        return None

    meta_path = folder / "metadata.json"
    if not meta_path.is_file():
        return None

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # Load psets
    psets: dict[str, dict[str, Any]] = {}
    psets_path = folder / "properties" / "psets.json"
    if psets_path.is_file():
        psets = json.loads(psets_path.read_text(encoding="utf-8"))

    # Load materials
    materials: list[MaterialLayer] = []
    mat_path = folder / "materials" / "materials.json"
    if mat_path.is_file():
        raw = json.loads(mat_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            materials = [MaterialLayer(**m) for m in raw]

    # Load geometry
    geometry = GeometryInfo()
    geo_path = folder / "geometry" / "shape.json"
    if geo_path.is_file():
        try:
            geometry = GeometryInfo.model_validate(
                json.loads(geo_path.read_text(encoding="utf-8"))
            )
        except Exception:
            pass

    # Load spatial
    spatial = SpatialReference()
    sp_path = folder / "relationships" / "spatial.json"
    if sp_path.is_file():
        try:
            spatial = SpatialReference.model_validate(
                json.loads(sp_path.read_text(encoding="utf-8"))
            )
        except Exception:
            pass

    return Element(
        global_id=meta.get("GlobalId", element_id),
        ifc_class=meta.get("IFCClass", ""),
        name=meta.get("Name"),
        object_type=meta.get("ObjectType"),
        tag=meta.get("Tag"),
        psets=psets,
        materials=materials,
        geometry=geometry,
        spatial=spatial,
    )


def update_element(
    project_root: Path,
    element_id: str,
    updates: dict[str, Any],
) -> Element:
    """Modify an existing element's metadata and properties.

    Supported update keys:
      - ``name``: change the element name
      - ``properties``: merge new property sets
      - ``materials``: replace material list

    Returns the updated :class:`Element`.

    Raises :class:`FileNotFoundError` if the element does not exist.
    """
    folder = _elements_dir(project_root) / f"element_{element_id}"
    if not folder.is_dir():
        raise FileNotFoundError(f"Element not found: {element_id}")

    meta_path = folder / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if "name" in updates:
        meta["Name"] = updates["name"]

    if "properties" in updates:
        # Merge new psets
        psets_path = folder / "properties" / "psets.json"
        psets = json.loads(psets_path.read_text(encoding="utf-8")) if psets_path.is_file() else {}
        for pset_name, props in updates["properties"].items():
            if pset_name not in psets:
                psets[pset_name] = {}
            psets[pset_name].update(props)
        (psets_path).write_text(json.dumps(psets, indent=2, default=str), encoding="utf-8")

        # Update flat psets in metadata
        flat: dict[str, Any] = {}
        for pset_name, props in psets.items():
            for prop_name, prop_val in props.items():
                flat[f"{pset_name}.{prop_name}"] = prop_val
        meta["Psets"] = flat

    if "materials" in updates:
        mat_dir = folder / "materials"
        mat_dir.mkdir(exist_ok=True)
        (mat_dir / "materials.json").write_text(
            json.dumps(updates["materials"], indent=2, default=str), encoding="utf-8"
        )

    # Write updated metadata
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    # Regenerate Markdown
    try:
        generate_metadata(folder)
    except Exception:
        logger.debug("Metadata regen failed for %s", element_id, exc_info=True)

    elem = get_element(project_root, element_id)
    if elem is None:
        raise FileNotFoundError(f"Element not found after update: {element_id}")
    return elem


def delete_element(project_root: Path, element_id: str) -> bool:
    """Remove an element folder.  Returns *True* if it existed."""
    folder = _elements_dir(project_root) / f"element_{element_id}"
    if folder.is_dir():
        shutil.rmtree(folder)
        logger.info("Deleted element %s", element_id)
        return True
    return False


def list_elements(
    project_root: Path,
    filters: dict[str, Any] | None = None,
) -> list[Element]:
    """List all elements in the project, optionally filtered.

    Supported filter keys:
      - ``ifc_class``: exact match on IFC class
      - ``name``: substring match on element name
      - ``material``: substring match on any material name
    """
    elem_dir = _elements_dir(project_root)
    if not elem_dir.is_dir():
        return []

    filters = filters or {}
    results: list[Element] = []

    for folder in sorted(elem_dir.iterdir()):
        if not folder.is_dir() or not folder.name.startswith("element_"):
            continue

        eid = folder.name.removeprefix("element_")
        elem = get_element(project_root, eid)
        if elem is None:
            continue

        # Apply filters
        if "ifc_class" in filters:
            if elem.ifc_class.lower() != filters["ifc_class"].lower():
                continue
        if "name" in filters:
            if elem.name and filters["name"].lower() not in elem.name.lower():
                continue
        if "material" in filters:
            mat_names = [m.name.lower() for m in elem.materials]
            if not any(filters["material"].lower() in mn for mn in mat_names):
                continue

        results.append(elem)

    return results
