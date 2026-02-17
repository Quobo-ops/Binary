"""Element — the atomic, reusable, versioned IFC-based design object.

Per the Business Logic Bible:
  'Element' is the primary term for the building block.
  Every Element is a self-contained folder of plain files (JSON + IFC).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Axis-aligned bounding box."""

    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0


class GeometryInfo(BaseModel):
    """Lightweight geometric summary of an element."""

    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    volume: float | None = None
    centroid: tuple[float, float, float] | None = None


class MaterialLayer(BaseModel):
    """A single material layer or constituent."""

    name: str = ""
    thickness: float | None = None
    category: str | None = None
    fraction: float | None = None


class SpatialReference(BaseModel):
    """Where an element lives in the spatial hierarchy."""

    site_name: str | None = None
    site_id: str | None = None
    building_name: str | None = None
    building_id: str | None = None
    storey_name: str | None = None
    storey_id: str | None = None


class Element(BaseModel):
    """The atomic unit of the AEC OS.

    Mirrors the per-element folder structure produced by the extraction pipeline:
      element_<GlobalId>/
        metadata.json, geometry/, properties/, materials/, relationships/
    """

    global_id: str
    ifc_class: str
    name: str | None = None
    object_type: str | None = None
    tag: str | None = None

    # Nested data sections
    geometry: GeometryInfo = Field(default_factory=GeometryInfo)
    psets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    materials: list[MaterialLayer] = Field(default_factory=list)
    spatial: SpatialReference = Field(default_factory=SpatialReference)
