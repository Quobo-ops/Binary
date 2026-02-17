"""Abstract ElementBuilder interface.

Every builder knows how to produce the JSON artefacts (metadata.json,
psets.json, materials.json, spatial.json, and bounding-box geometry) for
its IFC class, given a ParametricSpec.
"""

from __future__ import annotations

import abc
from typing import Any


class ElementBuilder(abc.ABC):
    """Base class for all element builders."""

    @property
    @abc.abstractmethod
    def ifc_class(self) -> str:
        """The canonical IFC class this builder produces."""

    @abc.abstractmethod
    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Return nested property-set dict for psets.json."""

    @abc.abstractmethod
    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        """Return list of material-layer dicts for materials.json."""

    @abc.abstractmethod
    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        """Return geometry info dict (bounding_box, volume, centroid) for shape.json."""

    def build_spatial(self) -> dict[str, Any]:
        """Return default spatial reference.  Override for custom placement."""
        return {
            "site_name": None,
            "site_id": None,
            "building_name": None,
            "building_id": None,
            "storey_name": None,
            "storey_id": None,
        }

    # Helpers shared by all builders

    @staticmethod
    def _mm_to_m(mm: float) -> float:
        return mm / 1000.0

    @staticmethod
    def _default_prop(props: dict[str, Any], key: str, default: float) -> float:
        """Get a numeric property, falling back to default."""
        val = props.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
        return default
