"""Rule-based regex fallback engine — always available, no external deps."""

from __future__ import annotations

from aecos.nlp.constraints import extract_constraints
from aecos.nlp.intent import classify_intent
from aecos.nlp.properties import (
    classify_ifc_class,
    extract_codes,
    extract_dimensions,
    extract_materials,
    extract_performance,
)
from aecos.nlp.providers.base import LLMProvider
from aecos.nlp.resolution import apply_context, compute_confidence, detect_ambiguities
from aecos.nlp.schema import ParametricSpec


class FallbackProvider(LLMProvider):
    """Pure rule-based engine using regex and keyword matching.

    Always available — no LLM dependency.  Produces lower confidence
    scores than an LLM provider but covers the core extraction pipeline.
    """

    def is_available(self) -> bool:
        """Always available."""
        return True

    def parse_with_llm(self, prompt: str) -> str | None:
        """Not used — this provider bypasses the LLM prompt path."""
        return None

    def parse(self, text: str, context: dict | None = None) -> ParametricSpec:
        """Parse *text* using regex rules and return a ParametricSpec."""
        intent = classify_intent(text)
        ifc_class = classify_ifc_class(text)
        dimensions = extract_dimensions(text)
        materials = extract_materials(text)
        performance = extract_performance(text)
        codes = extract_codes(text)
        constraints = extract_constraints(text)

        spec = ParametricSpec(
            intent=intent,
            ifc_class=ifc_class,
            properties=dimensions,
            materials=materials,
            performance=performance,
            compliance_codes=codes,
            constraints=constraints,
        )

        # Apply context enrichment
        spec = apply_context(spec, context)

        # Compute confidence and detect ambiguities
        spec.warnings = detect_ambiguities(spec, text)
        spec.confidence = compute_confidence(spec)

        return spec
