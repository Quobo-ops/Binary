"""Extract material associations from IFC elements."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element

from aecos.models.element import MaterialLayer

logger = logging.getLogger(__name__)


def extract_materials(element: ifcopenshell.entity_instance) -> list[MaterialLayer]:
    """Return material layers / constituents for *element*.

    Handles IfcMaterialLayerSetUsage, IfcMaterialConstituentSet,
    IfcMaterialList, and single IfcMaterial assignments.
    """
    try:
        mat = ifcopenshell.util.element.get_material(element)
    except Exception:
        logger.debug("Material extraction failed for %s", element.GlobalId, exc_info=True)
        return []

    if mat is None:
        return []

    layers: list[MaterialLayer] = []

    mat_type = mat.is_a()

    if mat_type == "IfcMaterial":
        layers.append(MaterialLayer(
            name=mat.Name or "",
            category=getattr(mat, "Category", None),
        ))

    elif mat_type == "IfcMaterialLayerSetUsage":
        layer_set = mat.ForLayerSet
        for layer in layer_set.MaterialLayers:
            layers.append(MaterialLayer(
                name=layer.Material.Name if layer.Material else "",
                thickness=layer.LayerThickness,
                category=getattr(layer, "Category", None),
            ))

    elif mat_type == "IfcMaterialLayerSet":
        for layer in mat.MaterialLayers:
            layers.append(MaterialLayer(
                name=layer.Material.Name if layer.Material else "",
                thickness=layer.LayerThickness,
                category=getattr(layer, "Category", None),
            ))

    elif mat_type == "IfcMaterialConstituentSet":
        for constituent in (mat.MaterialConstituents or []):
            layers.append(MaterialLayer(
                name=constituent.Material.Name if constituent.Material else "",
                category=getattr(constituent, "Category", None),
                fraction=getattr(constituent, "Fraction", None),
            ))

    elif mat_type == "IfcMaterialList":
        for m in mat.Materials:
            layers.append(MaterialLayer(name=m.Name or ""))

    return layers


def write_materials(materials: list[MaterialLayer], folder: Path) -> None:
    """Persist materials as ``materials/materials.json``."""
    mat_dir = folder / "materials"
    mat_dir.mkdir(parents=True, exist_ok=True)
    data = [m.model_dump(mode="json") for m in materials]
    (mat_dir / "materials.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
