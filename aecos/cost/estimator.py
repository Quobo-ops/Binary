"""Quantity takeoff from element metadata + unit pricing.

Calculates quantities entirely from JSON metadata — NO IFC geometry parsing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def calculate_quantities(
    ifc_class: str,
    properties: dict[str, Any],
) -> dict[str, float]:
    """Calculate quantity takeoff from element properties.

    All inputs are in mm (matching ParametricSpec convention).
    All outputs are in metric units (m, m2, m3).

    Returns dict with applicable keys: area_m2, volume_m3, length_m, count.
    """
    quantities: dict[str, float] = {}

    if ifc_class in ("IfcWall", "IfcWallStandardCase"):
        height_mm = _get_float(properties, "height_mm", 3000.0)
        length_mm = _get_float(properties, "length_mm", 5000.0)
        thickness_mm = _get_float(properties, "thickness_mm", 200.0)
        area_m2 = (height_mm / 1000.0) * (length_mm / 1000.0)
        volume_m3 = area_m2 * (thickness_mm / 1000.0)
        quantities["area_m2"] = round(area_m2, 4)
        quantities["volume_m3"] = round(volume_m3, 4)

    elif ifc_class == "IfcDoor":
        quantities["count"] = 1.0
        width_mm = _get_float(properties, "width_mm", 914.0)
        height_mm = _get_float(properties, "height_mm", 2134.0)
        quantities["area_m2"] = round(
            (width_mm / 1000.0) * (height_mm / 1000.0), 4
        )

    elif ifc_class == "IfcWindow":
        quantities["count"] = 1.0
        width_mm = _get_float(properties, "width_mm", 1200.0)
        height_mm = _get_float(properties, "height_mm", 1500.0)
        quantities["area_m2"] = round(
            (width_mm / 1000.0) * (height_mm / 1000.0), 4
        )

    elif ifc_class == "IfcSlab":
        length_mm = _get_float(properties, "length_mm", 6000.0)
        width_mm = _get_float(properties, "width_mm", 6000.0)
        thickness_mm = _get_float(properties, "thickness_mm", 200.0)
        area_m2 = (length_mm / 1000.0) * (width_mm / 1000.0)
        volume_m3 = area_m2 * (thickness_mm / 1000.0)
        quantities["area_m2"] = round(area_m2, 4)
        quantities["volume_m3"] = round(volume_m3, 4)

    elif ifc_class == "IfcColumn":
        width_mm = _get_float(properties, "width_mm", 400.0)
        height_mm = _get_float(properties, "height_mm", 3600.0)
        depth_mm = _get_float(properties, "depth_mm", width_mm)
        cross_section_m2 = (width_mm / 1000.0) * (depth_mm / 1000.0)
        volume_m3 = cross_section_m2 * (height_mm / 1000.0)
        quantities["volume_m3"] = round(volume_m3, 4)

    elif ifc_class == "IfcBeam":
        length_mm = _get_float(properties, "length_mm", 6000.0)
        depth_mm = _get_float(properties, "depth_mm", 500.0)
        width_mm = _get_float(properties, "width_mm", 300.0)
        cross_section_m2 = (depth_mm / 1000.0) * (width_mm / 1000.0)
        volume_m3 = cross_section_m2 * (length_mm / 1000.0)
        quantities["length_m"] = round(length_mm / 1000.0, 4)
        quantities["volume_m3"] = round(volume_m3, 4)

    else:
        # Generic fallback
        quantities["count"] = 1.0

    return quantities


def quantities_from_folder(element_folder: str | Path) -> tuple[str, dict[str, Any], dict[str, float]]:
    """Load element folder and calculate quantities.

    Returns (ifc_class, properties_dict, quantities).
    """
    folder = Path(element_folder)
    metadata = _load_json(folder / "metadata.json")
    psets = _load_json(folder / "properties" / "psets.json")

    ifc_class = metadata.get("IFCClass", "")

    # Gather dimensional properties from the Dimensions pset
    props: dict[str, Any] = {}
    dims = psets.get("Dimensions", {})
    props.update(dims)

    quantities = calculate_quantities(ifc_class, props)
    return ifc_class, props, quantities


def _get_float(d: dict[str, Any], key: str, default: float) -> float:
    val = d.get(key)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    return default


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
