"""WallBuilder — produces IfcWall / IfcWallStandardCase data."""

from __future__ import annotations

from typing import Any

from aecos.generation.builders.base import ElementBuilder


class WallBuilder(ElementBuilder):
    """Builder for wall elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcWall"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        thickness_mm = self._default_prop(props, "thickness_mm", 200.0)
        height_mm = self._default_prop(props, "height_mm", 3000.0)
        length_mm = self._default_prop(props, "length_mm", 5000.0)

        pset_common: dict[str, Any] = {
            "IsExternal": props.get("is_external", True),
            "LoadBearing": props.get("load_bearing", False),
            "Reference": props.get("reference", ""),
        }

        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]
        if perf.get("acoustic_stc"):
            pset_common["AcousticRating"] = perf["acoustic_stc"]
        if perf.get("thermal_r_value"):
            pset_common["ThermalTransmittance"] = perf["thermal_r_value"]

        dims: dict[str, Any] = {
            "thickness_mm": thickness_mm,
            "height_mm": height_mm,
            "length_mm": length_mm,
        }

        return {
            "Pset_WallCommon": pset_common,
            "Dimensions": dims,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        thickness_mm = self._default_prop(props, "thickness_mm", 200.0)
        if not material_names:
            material_names = ["Concrete"]

        if len(material_names) == 1:
            return [{"name": material_names[0], "thickness": thickness_mm, "category": "wall", "fraction": None}]

        # Multi-layer: split thickness evenly
        layer_t = thickness_mm / len(material_names)
        return [
            {"name": name, "thickness": round(layer_t, 1), "category": "wall", "fraction": None}
            for name in material_names
        ]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        t = self._mm_to_m(self._default_prop(props, "thickness_mm", 200.0))
        h = self._mm_to_m(self._default_prop(props, "height_mm", 3000.0))
        l = self._mm_to_m(self._default_prop(props, "length_mm", 5000.0))

        return {
            "bounding_box": {
                "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                "max_x": l, "max_y": t, "max_z": h,
            },
            "volume": round(l * t * h, 6),
            "centroid": (round(l / 2, 4), round(t / 2, 4), round(h / 2, 4)),
        }
