"""Property extraction — dimensions, materials, performance ratings, IFC mapping."""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Unit conversion helpers
# ---------------------------------------------------------------------------

_FEET_TO_MM = 304.8
_INCHES_TO_MM = 25.4
_METERS_TO_MM = 1000.0
_CM_TO_MM = 10.0


def _to_mm(value: float, unit: str) -> float:
    """Convert a value to millimetres."""
    unit = unit.lower().strip().rstrip("s").rstrip(".")
    if unit in ("foot", "feet", "ft", "'"):
        return round(value * _FEET_TO_MM, 1)
    if unit in ("inch", "in", "\"", "inche"):
        return round(value * _INCHES_TO_MM, 1)
    if unit in ("meter", "metre", "m"):
        return round(value * _METERS_TO_MM, 1)
    if unit in ("centimeter", "centimetre", "cm"):
        return round(value * _CM_TO_MM, 1)
    if unit in ("mm", "millimeter", "millimetre"):
        return round(value, 1)
    return round(value, 1)


# ---------------------------------------------------------------------------
# Dimension patterns
# ---------------------------------------------------------------------------

# Matches patterns like "12-foot", "12 foot", "12'", "12 ft"
_DIM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[-\s]?\s*"
    r"(foot|feet|ft|inch(?:es)?|in|meters?|metres?|m\b|cm|mm|centimeters?|centimetres?|"
    r"millimeters?|millimetres?|['\"])"
    r"(?:\s+(\d+(?:\.\d+)?)\s*[-\s]?\s*(inch(?:es)?|in|[\"]))?"  # optional inches after feet
    ,
    re.I,
)

_DIM_QUALIFIERS = {
    "tall": "height_mm",
    "high": "height_mm",
    "height": "height_mm",
    "wide": "width_mm",
    "width": "width_mm",
    "thick": "thickness_mm",
    "thickness": "thickness_mm",
    "deep": "depth_mm",
    "depth": "depth_mm",
    "long": "length_mm",
    "length": "length_mm",
}

_QUALIFIER_RE = re.compile(
    r"\b(" + "|".join(_DIM_QUALIFIERS.keys()) + r")\b",
    re.I,
)


def extract_dimensions(text: str) -> dict[str, float]:
    """Extract dimensional properties from *text*, returning values in mm."""
    dims: dict[str, float] = {}

    for match in _DIM_RE.finditer(text):
        value = float(match.group(1))
        unit = match.group(2)
        mm = _to_mm(value, unit)

        # Handle feet + inches combo (e.g., "6 feet 4 inches")
        if match.group(3) and match.group(4):
            extra_inches = float(match.group(3))
            mm += _to_mm(extra_inches, match.group(4))
            mm = round(mm, 1)

        # Find the closest qualifier after this dimension
        rest = text[match.end():]
        qualifier_match = _QUALIFIER_RE.search(rest[:30])  # look ahead 30 chars
        if qualifier_match:
            key = _DIM_QUALIFIERS[qualifier_match.group(1).lower()]
        else:
            # Try qualifier before the dimension
            before = text[:match.start()]
            qualifier_before = None
            for qm in _QUALIFIER_RE.finditer(before):
                qualifier_before = qm
            if qualifier_before and (match.start() - qualifier_before.end()) < 20:
                key = _DIM_QUALIFIERS[qualifier_before.group(1).lower()]
            elif not dims:
                # First unqualified dimension — guess based on IFC class context
                key = "height_mm"
            elif "width_mm" not in dims:
                key = "width_mm"
            elif "thickness_mm" not in dims:
                key = "thickness_mm"
            else:
                key = "length_mm"

        dims[key] = mm

    return dims


# ---------------------------------------------------------------------------
# Material extraction
# ---------------------------------------------------------------------------

_MATERIALS: list[str] = [
    "concrete",
    "steel",
    "gypsum",
    "glass",
    "wood",
    "cmu",
    "brick",
    "aluminum",
    "aluminium",
    "timber",
    "masonry",
    "plywood",
    "drywall",
    "stucco",
    "insulation",
    "fiberglass",
    "copper",
    "stone",
    "granite",
    "marble",
    "ceramic",
    "vinyl",
    "metal",
]

_MATERIAL_RE = re.compile(
    r"\b(" + "|".join(_MATERIALS) + r")\b",
    re.I,
)


def extract_materials(text: str) -> list[str]:
    """Return a deduplicated list of material keywords found in *text*."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _MATERIAL_RE.finditer(text):
        mat = m.group(1).lower()
        # Normalise aluminium -> aluminum
        if mat == "aluminium":
            mat = "aluminum"
        if mat not in seen:
            seen.add(mat)
            result.append(mat)
    return result


# ---------------------------------------------------------------------------
# Performance attributes
# ---------------------------------------------------------------------------

_FIRE_RATING_RE = re.compile(
    r"(\d+)\s*[-\s]?\s*(?:hour|hr)\s*(?:fire\s*[-\s]?\s*rat(?:ed|ing))?",
    re.I,
)

_FIRE_RATED_RE = re.compile(
    r"fire\s*[-\s]?\s*rat(?:ed|ing)\s*(?:for\s*)?(\d+)\s*[-\s]?\s*(?:hour|hr)",
    re.I,
)

_STC_RE = re.compile(r"\bSTC\s*[-:]?\s*(\d+)", re.I)

_R_VALUE_RE = re.compile(r"\bR\s*[-:]?\s*(\d+(?:\.\d+)?)", re.I)

_U_VALUE_RE = re.compile(r"\bU\s*[-:]?\s*(\d+(?:\.\d+)?)", re.I)


def extract_performance(text: str) -> dict[str, Any]:
    """Extract performance ratings from *text*."""
    perf: dict[str, Any] = {}

    # Fire rating
    m = _FIRE_RATED_RE.search(text) or _FIRE_RATING_RE.search(text)
    if m:
        hours = int(m.group(1))
        perf["fire_rating"] = f"{hours}H"
    elif re.search(r"\bfire\s*[-\s]?\s*rat(?:ed|ing)\b", text, re.I):
        # Fire-rated but no duration specified
        perf["fire_rating"] = "rated"

    # Acoustic STC
    m = _STC_RE.search(text)
    if m:
        perf["acoustic_stc"] = int(m.group(1))

    # Thermal R-value
    m = _R_VALUE_RE.search(text)
    if m:
        perf["thermal_r_value"] = float(m.group(1))

    # Thermal U-value
    m = _U_VALUE_RE.search(text)
    if m:
        perf["thermal_u_value"] = float(m.group(1))

    return perf


# ---------------------------------------------------------------------------
# IFC class mapping
# ---------------------------------------------------------------------------

_IFC_CLASS_MAP: dict[str, str] = {
    "wall": "IfcWall",
    "door": "IfcDoor",
    "window": "IfcWindow",
    "beam": "IfcBeam",
    "column": "IfcColumn",
    "slab": "IfcSlab",
    "roof": "IfcRoof",
    "stair": "IfcStairFlight",
    "stairs": "IfcStairFlight",
    "ramp": "IfcRamp",
    "curtain wall": "IfcCurtainWall",
    "railing": "IfcRailing",
    "plate": "IfcPlate",
    "footing": "IfcFooting",
    "pile": "IfcPile",
    "member": "IfcMember",
    "covering": "IfcCovering",
    "ceiling": "IfcCovering",
    "floor": "IfcSlab",
    "pipe": "IfcPipeSegment",
    "duct": "IfcDuctSegment",
    "hvac": "IfcEnergyConversionDevice",
    "parking": "IfcSpace",
}

_IFC_RE = re.compile(
    r"\b(" + "|".join(sorted(_IFC_CLASS_MAP.keys(), key=len, reverse=True)) + r")\b",
    re.I,
)


def classify_ifc_class(text: str) -> str:
    """Return the best-matching IFC class for *text*, or empty string."""
    m = _IFC_RE.search(text)
    if m:
        return _IFC_CLASS_MAP[m.group(1).lower()]
    return ""


# ---------------------------------------------------------------------------
# Code reference extraction
# ---------------------------------------------------------------------------

_CODE_MAP: dict[str, str] = {
    "ibc": "IBC2024",
    "international building code": "IBC2024",
    "cbc": "CBC2025",
    "california building code": "CBC2025",
    "title 24": "Title-24",
    "title-24": "Title-24",
    "title24": "Title-24",
    "ada": "ADA2010",
    "americans with disabilities": "ADA2010",
    "iecc": "IECC2024",
    "international energy": "IECC2024",
    "asce 7": "ASCE7-22",
    "asce7": "ASCE7-22",
    "aci 318": "ACI318-19",
    "aci318": "ACI318-19",
    "nfpa": "NFPA",
    "ashrae": "ASHRAE90.1",
}

_CODE_RE = re.compile(
    r"\b(" + "|".join(
        re.escape(k) for k in sorted(_CODE_MAP.keys(), key=len, reverse=True)
    ) + r")\b",
    re.I,
)

# Also match patterns like "IBC-703", "ADA 2010 §1106"
_CODE_SECTION_RE = re.compile(
    r"\b(IBC|CBC|ADA|IECC|NFPA|ASCE|ACI)\s*[-]?\s*(\d[\d.]*)",
    re.I,
)


def extract_codes(text: str) -> list[str]:
    """Return a deduplicated list of code references found in *text*."""
    seen: set[str] = set()
    result: list[str] = []

    # Match named codes
    for m in _CODE_RE.finditer(text):
        code = _CODE_MAP[m.group(1).lower()]
        if code not in seen:
            seen.add(code)
            result.append(code)

    # Match section references like "IBC-703"
    for m in _CODE_SECTION_RE.finditer(text):
        prefix = m.group(1).upper()
        section = m.group(2)
        ref = f"{prefix}-{section}"
        if ref not in seen:
            seen.add(ref)
            result.append(ref)

    return result
