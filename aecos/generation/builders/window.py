"""WindowBuilder — produces IfcWindow data."""

from __future__ import annotations

from typing import Any

from aecos.generation.builders.base import ElementBuilder


class WindowBuilder(ElementBuilder):
    """Builder for window elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcWindow"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        width_mm = self._default_prop(props, "width_mm", 1200.0)
        height_mm = self._default_prop(props, "height_mm", 1500.0)

        pset_common: dict[str, Any] = {
            "IsExternal": props.get("is_external", True),
            "Reference": props.get("reference", ""),
            "GlazingType": props.get("glazing_type", "double"),
        }

        if perf.get("thermal_u_value"):
            pset_common["ThermalTransmittance"] = perf["thermal_u_value"]
        if perf.get("shgc"):
            pset_common["SolarHeatGainCoefficient"] = perf["shgc"]
        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]

        dims: dict[str, Any] = {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "sill_height_mm": self._default_prop(props, "sill_height_mm", 900.0),
        }

        return {
            "Pset_WindowCommon": pset_common,
            "Dimensions": dims,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        if not material_names:
            material_names = ["Glass"]
        return [{"name": name, "thickness": None, "category": "window", "fraction": None} for name in material_names]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        w = self._mm_to_m(self._default_prop(props, "width_mm", 1200.0))
        h = self._mm_to_m(self._default_prop(props, "height_mm", 1500.0))
        d = 0.03  # standard window thickness ~30mm

        return {
            "bounding_box": {
                "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                "max_x": w, "max_y": d, "max_z": h,
            },
            "volume": round(w * d * h, 6),
            "centroid": (round(w / 2, 4), round(d / 2, 4), round(h / 2, 4)),
        }
