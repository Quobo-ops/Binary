"""SlabBuilder — produces IfcSlab data."""

from __future__ import annotations

from typing import Any

from aecos.generation.builders.base import ElementBuilder


class SlabBuilder(ElementBuilder):
    """Builder for slab elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcSlab"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        thickness_mm = self._default_prop(props, "thickness_mm", 200.0)
        length_mm = self._default_prop(props, "length_mm", 6000.0)
        width_mm = self._default_prop(props, "width_mm", 6000.0)

        pset_common: dict[str, Any] = {
            "IsExternal": props.get("is_external", False),
            "LoadBearing": props.get("load_bearing", True),
            "Reference": props.get("reference", ""),
        }

        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]

        dims: dict[str, Any] = {
            "thickness_mm": thickness_mm,
            "length_mm": length_mm,
            "width_mm": width_mm,
            "slope": props.get("slope", 0.0),
        }

        rebar: dict[str, Any] = {
            "reinforcement": props.get("reinforcement", "standard"),
        }

        return {
            "Pset_SlabCommon": pset_common,
            "Dimensions": dims,
            "Reinforcement": rebar,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        thickness_mm = self._default_prop(props, "thickness_mm", 200.0)
        if not material_names:
            material_names = ["Concrete"]
        return [
            {"name": name, "thickness": thickness_mm / len(material_names), "category": "slab", "fraction": None}
            for name in material_names
        ]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        t = self._mm_to_m(self._default_prop(props, "thickness_mm", 200.0))
        l = self._mm_to_m(self._default_prop(props, "length_mm", 6000.0))
        w = self._mm_to_m(self._default_prop(props, "width_mm", 6000.0))

        return {
            "bounding_box": {
                "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                "max_x": l, "max_y": w, "max_z": t,
            },
            "volume": round(l * w * t, 6),
            "centroid": (round(l / 2, 4), round(w / 2, 4), round(t / 2, 4)),
        }
