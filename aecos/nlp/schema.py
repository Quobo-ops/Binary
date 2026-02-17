"""ParametricSpec — the structured output of the natural-language parser.

Per the Business Logic Bible:
  'Parametric Spec' is the structured output of the natural-language parser
  that drives generation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParametricSpec(BaseModel):
    """Structured specification extracted from natural-language input.

    All dimensions are stored in millimetres internally.
    """

    intent: str = "create"
    """Action intent: 'create', 'modify', 'find', or 'validate'."""

    ifc_class: str = ""
    """Mapped IFC entity type (e.g. 'IfcWall', 'IfcDoor')."""

    name: str | None = None
    """Optional human-readable name extracted from the input."""

    properties: dict[str, Any] = Field(default_factory=dict)
    """Extracted dimensional properties — all lengths in mm.

    Common keys: height_mm, width_mm, thickness_mm, area_m2, length_mm.
    """

    materials: list[str] = Field(default_factory=list)
    """Material keywords found in the input."""

    performance: dict[str, Any] = Field(default_factory=dict)
    """Performance attributes.

    Common keys: fire_rating, acoustic_stc, thermal_r_value,
    thermal_u_value, efficiency.
    """

    constraints: dict[str, Any] = Field(default_factory=dict)
    """Parsed constraints.

    Common keys: accessibility, energy_code, structural, placement.
    """

    compliance_codes: list[str] = Field(default_factory=list)
    """Referenced building codes (e.g. 'IBC2024', 'ADA2010', 'Title-24')."""

    confidence: float = 0.0
    """Overall parse confidence, 0.0 to 1.0."""

    warnings: list[str] = Field(default_factory=list)
    """Ambiguities, assumptions, or missing information."""
