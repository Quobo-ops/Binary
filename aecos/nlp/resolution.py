"""Ambiguity resolution and confidence scoring."""

from __future__ import annotations

from aecos.nlp.schema import ParametricSpec


def compute_confidence(spec: ParametricSpec) -> float:
    """Compute an overall confidence score (0.0–1.0) for a parsed spec.

    The score is based on how many fields were successfully populated:
      - ifc_class identified: +0.25
      - at least one dimension:  +0.20
      - at least one material:   +0.15
      - performance data:        +0.15
      - compliance codes:        +0.10
      - constraints:             +0.10
      - name extracted:          +0.05
    """
    score = 0.0

    if spec.ifc_class:
        score += 0.25
    if spec.properties:
        score += 0.20
    if spec.materials:
        score += 0.15
    if spec.performance:
        score += 0.15
    if spec.compliance_codes:
        score += 0.10
    if spec.constraints:
        score += 0.10
    if spec.name:
        score += 0.05

    return round(min(score, 1.0), 2)


def detect_ambiguities(spec: ParametricSpec, text: str) -> list[str]:
    """Return a list of warnings about ambiguities or assumptions.

    Checks for common issues:
      - Missing IFC class
      - No dimensions provided
      - Fire-rated but no duration
      - Vague input (very short text)
      - No materials specified for structural elements
    """
    warnings: list[str] = []

    if not spec.ifc_class:
        warnings.append("Could not determine IFC element type from input.")

    if not spec.properties:
        warnings.append("No dimensions found — sizes will use defaults.")

    word_count = len(text.split())
    if word_count < 3:
        warnings.append("Input is very brief — interpretation may be incomplete.")

    if spec.performance.get("fire_rating") == "rated":
        warnings.append(
            "Fire-rated mentioned but no duration specified — assuming minimum code requirement."
        )

    structural_classes = {"IfcBeam", "IfcColumn", "IfcSlab", "IfcFooting"}
    if spec.ifc_class in structural_classes and not spec.materials:
        warnings.append(
            f"Structural element ({spec.ifc_class}) with no material specified — "
            "material will need to be determined."
        )

    return warnings


def apply_context(spec: ParametricSpec, context: dict | None) -> ParametricSpec:
    """Enrich the spec with contextual defaults.

    Supported context keys:
      - ``jurisdiction``: if provided, adds region-specific code references
      - ``climate_zone``: if provided, adds to energy_code constraint
      - ``project_type``: stored in constraints for downstream use
    """
    if not context:
        return spec

    jurisdiction = context.get("jurisdiction", "").lower()
    if jurisdiction:
        if "california" in jurisdiction or jurisdiction == "ca":
            if "CBC2025" not in spec.compliance_codes:
                spec.compliance_codes.append("CBC2025")
            if "Title-24" not in spec.compliance_codes:
                spec.compliance_codes.append("Title-24")
        # Always include IBC for US jurisdictions
        if any(kw in jurisdiction for kw in ("us", "california", "louisiana", "la", "ca")):
            if "IBC2024" not in spec.compliance_codes:
                spec.compliance_codes.append("IBC2024")

    climate_zone = context.get("climate_zone")
    if climate_zone:
        if "energy_code" not in spec.constraints:
            spec.constraints["energy_code"] = {"required": True}
        spec.constraints["energy_code"]["climate_zone"] = climate_zone

    project_type = context.get("project_type")
    if project_type:
        spec.constraints["project_type"] = project_type

    return spec
