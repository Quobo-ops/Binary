"""DoorBuilder — produces IfcDoor data."""

from __future__ import annotations

from typing import Any

from aecos.generation.builders.base import ElementBuilder


class DoorBuilder(ElementBuilder):
    """Builder for door elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcDoor"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        width_mm = self._default_prop(props, "width_mm", 914.0)
        height_mm = self._default_prop(props, "height_mm", 2134.0)

        pset_common: dict[str, Any] = {
            "IsExternal": props.get("is_external", False),
            "Reference": props.get("reference", ""),
            "HandicapAccessible": props.get("handicap_accessible", False),
        }

        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]
        if perf.get("acoustic_stc"):
            pset_common["AcousticRating"] = perf["acoustic_stc"]

        dims: dict[str, Any] = {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "swing_direction": props.get("swing_direction", "left"),
        }

        hardware: dict[str, Any] = {
            "hardware_type": props.get("hardware_type", "lever"),
            "closer": props.get("closer", False),
        }

        return {
            "Pset_DoorCommon": pset_common,
            "Dimensions": dims,
            "Hardware": hardware,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        if not material_names:
            material_names = ["Wood"]
        return [{"name": name, "thickness": None, "category": "door", "fraction": None} for name in material_names]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        w = self._mm_to_m(self._default_prop(props, "width_mm", 914.0))
        h = self._mm_to_m(self._default_prop(props, "height_mm", 2134.0))
        d = 0.05  # standard door thickness ~50mm

        return {
            "bounding_box": {
                "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                "max_x": w, "max_y": d, "max_z": h,
            },
            "volume": round(w * d * h, 6),
            "centroid": (round(w / 2, 4), round(d / 2, 4), round(h / 2, 4)),
        }
