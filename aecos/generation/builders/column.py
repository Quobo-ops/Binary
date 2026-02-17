"""ColumnBuilder — produces IfcColumn data."""

from __future__ import annotations

import math
from typing import Any

from aecos.generation.builders.base import ElementBuilder


class ColumnBuilder(ElementBuilder):
    """Builder for column elements."""

    @property
    def ifc_class(self) -> str:
        return "IfcColumn"

    def build_psets(self, props: dict[str, Any], perf: dict[str, Any]) -> dict[str, dict[str, Any]]:
        width_mm = self._default_prop(props, "width_mm", 400.0)
        height_mm = self._default_prop(props, "height_mm", 3600.0)
        shape = props.get("shape", "rectangular")

        pset_common: dict[str, Any] = {
            "LoadBearing": props.get("load_bearing", True),
            "Reference": props.get("reference", ""),
        }

        if perf.get("fire_rating"):
            pset_common["FireRating"] = perf["fire_rating"]

        dims: dict[str, Any] = {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "shape": shape,
        }

        if shape == "circular":
            dims["diameter_mm"] = self._default_prop(props, "diameter_mm", width_mm)
        else:
            dims["depth_mm"] = self._default_prop(props, "depth_mm", width_mm)

        rebar: dict[str, Any] = {
            "reinforcement": props.get("reinforcement", "standard"),
        }

        return {
            "Pset_ColumnCommon": pset_common,
            "Dimensions": dims,
            "Reinforcement": rebar,
        }

    def build_materials(self, material_names: list[str], props: dict[str, Any]) -> list[dict[str, Any]]:
        if not material_names:
            material_names = ["Concrete"]
        return [{"name": name, "thickness": None, "category": "column", "fraction": None} for name in material_names]

    def build_geometry(self, props: dict[str, Any]) -> dict[str, Any]:
        w = self._mm_to_m(self._default_prop(props, "width_mm", 400.0))
        h = self._mm_to_m(self._default_prop(props, "height_mm", 3600.0))
        shape = props.get("shape", "rectangular")

        if shape == "circular":
            d = self._mm_to_m(self._default_prop(props, "diameter_mm", w * 1000.0))
            r = d / 2
            area = math.pi * r * r
            volume = area * h
            # Bounding box encloses the circle
            return {
                "bounding_box": {
                    "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                    "max_x": d, "max_y": d, "max_z": h,
                },
                "volume": round(volume, 6),
                "centroid": (round(d / 2, 4), round(d / 2, 4), round(h / 2, 4)),
            }
        else:
            depth = self._mm_to_m(self._default_prop(props, "depth_mm", w * 1000.0))
            return {
                "bounding_box": {
                    "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                    "max_x": w, "max_y": depth, "max_z": h,
                },
                "volume": round(w * depth * h, 6),
                "centroid": (round(w / 2, 4), round(depth / 2, 4), round(h / 2, 4)),
            }
