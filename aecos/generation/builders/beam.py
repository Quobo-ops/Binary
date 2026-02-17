"""BeamBuilder — produces IfcBeam data."""

from __future__ import annotations

from typing import Any

from aecos.generation.builders.base import ElementBuilder


class BeamBuilder(ElementBuilder):
    """Builder for beam elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcBeam"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        depth_mm = self._default_prop(props, "depth_mm", 500.0)
        width_mm = self._default_prop(props, "width_mm", 300.0)
        span_mm = self._default_prop(props, "length_mm", 6000.0)
        profile_type = props.get("profile_type", "W")

        pset_common: dict[str, Any] = {
            "LoadBearing": props.get("load_bearing", True),
            "Reference": props.get("reference", ""),
            "Span": span_mm,
        }

        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]

        dims: dict[str, Any] = {
            "depth_mm": depth_mm,
            "width_mm": width_mm,
            "length_mm": span_mm,
            "profile_type": profile_type,
        }

        return {
            "Pset_BeamCommon": pset_common,
            "Dimensions": dims,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        if not material_names:
            material_names = ["Steel"]
        return [{"name": name, "thickness": None, "category": "beam", "fraction": None} for name in material_names]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        d = self._mm_to_m(self._default_prop(props, "depth_mm", 500.0))
        w = self._mm_to_m(self._default_prop(props, "width_mm", 300.0))
        l = self._mm_to_m(self._default_prop(props, "length_mm", 6000.0))

        return {
            "bounding_box": {
                "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                "max_x": l, "max_y": w, "max_z": d,
            },
            "volume": round(l * w * d, 6),
            "centroid": (round(l / 2, 4), round(w / 2, 4), round(d / 2, 4)),
        }
