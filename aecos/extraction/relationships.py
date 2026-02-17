"""Extract spatial and type relationships from IFC elements."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import ifcopenshell

from aecos.models.element import SpatialReference

logger = logging.getLogger(__name__)


def extract_spatial(element: ifcopenshell.entity_instance) -> SpatialReference:
    """Walk IfcRelContainedInSpatialStructure to find the parent storey/building/site."""
    ref = SpatialReference()

    try:
        # ContainedInStructure is an inverse attribute on IfcElement
        containment_rels = getattr(element, "ContainedInStructure", None)
        if not containment_rels:
            return ref

        # An element is typically contained in exactly one spatial structure
        spatial = containment_rels[0].RelatingStructure

        # Walk up the spatial hierarchy
        current = spatial
        while current is not None:
            cls = current.is_a()
            if cls == "IfcBuildingStorey":
                ref.storey_name = current.Name
                ref.storey_id = current.GlobalId
            elif cls == "IfcBuilding":
                ref.building_name = current.Name
                ref.building_id = current.GlobalId
            elif cls == "IfcSite":
                ref.site_name = current.Name
                ref.site_id = current.GlobalId

            # Move up via IfcRelAggregates (Decomposes inverse)
            decomposes = getattr(current, "Decomposes", None)
            if decomposes:
                current = decomposes[0].RelatingObject
            else:
                current = None
    except Exception:
        logger.debug(
            "Spatial extraction failed for %s", element.GlobalId, exc_info=True
        )

    return ref


def write_spatial(ref: SpatialReference, folder: Path) -> None:
    """Persist spatial relationships as ``relationships/spatial.json``."""
    rel_dir = folder / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    (rel_dir / "spatial.json").write_text(
        json.dumps(ref.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
