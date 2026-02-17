"""Extract geometry representations from IFC elements.

Computes bounding box, volume, and centroid using ifcopenshell's geometry
engine when available, with a safe fallback to empty/zero values.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import ifcopenshell

from aecos.models.element import BoundingBox, GeometryInfo

logger = logging.getLogger(__name__)

# Try to import geometry processing; not every environment has OCC bindings.
try:
    import ifcopenshell.geom

    _HAS_GEOM = True
except ImportError:
    _HAS_GEOM = False


def _settings() -> Any:
    """Return ifcopenshell geometry settings."""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    return settings


def extract_geometry(
    element: ifcopenshell.entity_instance,
    ifc_file: ifcopenshell.file,
) -> GeometryInfo:
    """Return a GeometryInfo for *element*.

    If the geometry kernel is available and the element has a representation,
    this computes the axis-aligned bounding box, volume, and centroid from
    the triangulated shape.  Otherwise it returns a zeroed-out object.
    """
    if not _HAS_GEOM or element.Representation is None:
        return GeometryInfo()

    try:
        shape = ifcopenshell.geom.create_shape(_settings(), element)
        verts = shape.geometry.verts
        if not verts:
            return GeometryInfo()

        xs = verts[0::3]
        ys = verts[1::3]
        zs = verts[2::3]

        bbox = BoundingBox(
            min_x=min(xs),
            min_y=min(ys),
            min_z=min(zs),
            max_x=max(xs),
            max_y=max(ys),
            max_z=max(zs),
        )

        cx = (bbox.min_x + bbox.max_x) / 2
        cy = (bbox.min_y + bbox.max_y) / 2
        cz = (bbox.min_z + bbox.max_z) / 2

        dx = bbox.max_x - bbox.min_x
        dy = bbox.max_y - bbox.min_y
        dz = bbox.max_z - bbox.min_z
        volume = dx * dy * dz  # bounding-box volume approximation

        return GeometryInfo(
            bounding_box=bbox,
            volume=volume,
            centroid=(cx, cy, cz),
        )
    except Exception:
        logger.debug("Geometry extraction failed for %s", element.GlobalId, exc_info=True)
        return GeometryInfo()


def write_geometry(info: GeometryInfo, folder: Path) -> None:
    """Persist geometry info as ``geometry/shape.json``."""
    geo_dir = folder / "geometry"
    geo_dir.mkdir(parents=True, exist_ok=True)
    (geo_dir / "shape.json").write_text(
        json.dumps(info.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
