"""Constraint parsing — accessibility, energy, fire, structural constraints."""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Accessibility
# ---------------------------------------------------------------------------

_ACCESSIBILITY_RE = re.compile(
    r"\b(ada|accessible|accessibility|wheelchair|mobility|barrier[- ]?free|"
    r"universal\s*design|handicap)\b",
    re.I,
)


def extract_accessibility(text: str) -> dict[str, Any] | None:
    """Return accessibility constraint dict if relevant keywords found."""
    if _ACCESSIBILITY_RE.search(text):
        constraints: dict[str, Any] = {"required": True, "standard": "ADA2010"}

        # Check for specific provisions
        if re.search(r"\bvan\s*[-\s]?accessible\b", text, re.I):
            constraints["van_accessible"] = True
        if re.search(r"\bparking\b", text, re.I):
            constraints["type"] = "parking"
        if re.search(r"\broute\b", text, re.I):
            constraints["accessible_route"] = True

        return constraints
    return None


# ---------------------------------------------------------------------------
# Energy code
# ---------------------------------------------------------------------------

_ENERGY_RE = re.compile(
    r"\b(title\s*24|iecc|energy\s*code|energy\s*efficient|high[- ]efficiency|"
    r"insulation|thermal|r[- ]?value|u[- ]?value)\b",
    re.I,
)

_CLIMATE_ZONE_RE = re.compile(r"\bclimate\s*zone\s*(\d[A-C]?)\b", re.I)


def extract_energy(text: str) -> dict[str, Any] | None:
    """Return energy-code constraint dict if relevant keywords found."""
    if _ENERGY_RE.search(text):
        constraints: dict[str, Any] = {"required": True}

        if re.search(r"\btitle\s*24\b", text, re.I):
            constraints["code"] = "Title-24"
        elif re.search(r"\biecc\b", text, re.I):
            constraints["code"] = "IECC2024"

        m = _CLIMATE_ZONE_RE.search(text)
        if m:
            constraints["climate_zone"] = m.group(1)

        return constraints
    return None


# ---------------------------------------------------------------------------
# Fire safety
# ---------------------------------------------------------------------------

_FIRE_RE = re.compile(
    r"\b(fire[- ]?rat(?:ed|ing)|fire[- ]?resist|fire[- ]?barrier|"
    r"fire[- ]?separation|fire[- ]?wall|smoke[- ]?barrier|"
    r"fire[- ]?stop|fire[- ]?proof)\b",
    re.I,
)


def extract_fire(text: str) -> dict[str, Any] | None:
    """Return fire-safety constraint dict if relevant keywords found."""
    if _FIRE_RE.search(text):
        constraints: dict[str, Any] = {"required": True}

        # Duration
        m = re.search(r"(\d+)\s*[-\s]?\s*(?:hour|hr)", text, re.I)
        if m:
            constraints["duration_hours"] = int(m.group(1))

        if re.search(r"\bsmoke[- ]?barrier\b", text, re.I):
            constraints["type"] = "smoke_barrier"
        elif re.search(r"\bfire[- ]?wall\b", text, re.I):
            constraints["type"] = "fire_wall"
        elif re.search(r"\bfire[- ]?barrier\b", text, re.I):
            constraints["type"] = "fire_barrier"

        return constraints
    return None


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------

_STRUCTURAL_RE = re.compile(
    r"\b(load[- ]?bearing|structural|seismic|lateral|shear|"
    r"reinforced|post[- ]?tension|prestress)\b",
    re.I,
)

_SEISMIC_CAT_RE = re.compile(r"\bseismic\s*(?:design\s*)?category\s*([A-F])\b", re.I)


def extract_structural(text: str) -> dict[str, Any] | None:
    """Return structural constraint dict if relevant keywords found."""
    if _STRUCTURAL_RE.search(text):
        constraints: dict[str, Any] = {"required": True}

        if re.search(r"\bload[- ]?bearing\b", text, re.I):
            constraints["load_bearing"] = True
        if re.search(r"\breinforced\b", text, re.I):
            constraints["reinforced"] = True

        m = _SEISMIC_CAT_RE.search(text)
        if m:
            constraints["seismic_design_category"] = m.group(1).upper()

        return constraints
    return None


# ---------------------------------------------------------------------------
# Placement constraints
# ---------------------------------------------------------------------------

_BETWEEN_RE = re.compile(r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\s*[,.]|\s*$)", re.I)
_FLOOR_RE = re.compile(r"\bfloors?\s*(\d+)(?:\s*[-–]\s*(\d+))?\b", re.I)
_EXTERIOR_RE = re.compile(r"\b(exterior|external|outside|outdoor)\b", re.I)
_INTERIOR_RE = re.compile(r"\b(interior|internal|inside|indoor)\b", re.I)


def extract_placement(text: str) -> dict[str, Any] | None:
    """Return placement constraint dict if relevant keywords found."""
    constraints: dict[str, Any] = {}

    m = _BETWEEN_RE.search(text)
    if m:
        constraints["between"] = [m.group(1).strip(), m.group(2).strip()]

    m = _FLOOR_RE.search(text)
    if m:
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        constraints["floors"] = list(range(start, end + 1))

    if _EXTERIOR_RE.search(text):
        constraints["location"] = "exterior"
    elif _INTERIOR_RE.search(text):
        constraints["location"] = "interior"

    return constraints if constraints else None


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def extract_constraints(text: str) -> dict[str, Any]:
    """Extract all constraints from *text* and return a merged dict."""
    result: dict[str, Any] = {}

    acc = extract_accessibility(text)
    if acc:
        result["accessibility"] = acc

    energy = extract_energy(text)
    if energy:
        result["energy_code"] = energy

    fire = extract_fire(text)
    if fire:
        result["fire"] = fire

    structural = extract_structural(text)
    if structural:
        result["structural"] = structural

    placement = extract_placement(text)
    if placement:
        result["placement"] = placement

    return result
