"""NLParser — main entry point for natural-language parsing.

Usage::

    from aecos.nlp import NLParser

    parser = NLParser()
    spec = parser.parse("2-hour fire-rated concrete wall, 12 feet tall")
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from aecos.nlp.providers.base import LLMProvider
from aecos.nlp.providers.fallback import FallbackProvider
from aecos.nlp.providers.ollama import OllamaProvider
from aecos.nlp.resolution import apply_context, compute_confidence, detect_ambiguities
from aecos.nlp.schema import ParametricSpec

if TYPE_CHECKING:
    from aecos.finetune.collector import InteractionCollector

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an AEC (Architecture, Engineering, Construction) specification parser.
Given a plain-English building description, extract structured parameters.

Return a JSON object with these fields:
- intent: "create", "modify", "find", or "validate"
- ifc_class: IFC entity type (IfcWall, IfcDoor, IfcWindow, IfcBeam, IfcColumn, IfcSlab, etc.)
- properties: dict of dimensional properties (height_mm, width_mm, thickness_mm — all in mm)
- materials: list of material names
- performance: dict (fire_rating as "2H", acoustic_stc, thermal_r_value, etc.)
- compliance_codes: list of code references ("IBC2024", "ADA2010", "Title-24", etc.)
- constraints: dict of constraints (accessibility, energy_code, structural, placement)

Convert all dimensions to millimetres. 1 foot = 304.8 mm, 1 inch = 25.4 mm.
"""


class NLParser:
    """Natural language parser for AEC building descriptions.

    Tries an LLM provider first, automatically falling back to the
    rule-based regex engine if the LLM is unavailable.

    Parameters
    ----------
    provider:
        An explicit :class:`LLMProvider` to use.  If *None*, the parser
        tries :class:`OllamaProvider` then falls back to
        :class:`FallbackProvider`.
    collector:
        Optional :class:`InteractionCollector` for fine-tuning data
        collection.  When set, every ``parse()`` call auto-logs the
        interaction.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        collector: InteractionCollector | None = None,
    ) -> None:
        self._fallback = FallbackProvider()
        self._collector = collector
        if provider is not None:
            self._provider = provider
        else:
            self._provider = OllamaProvider()

    def parse(self, text: str, context: dict[str, Any] | None = None) -> ParametricSpec:
        """Parse a plain-English building description into a ParametricSpec.

        Parameters
        ----------
        text:
            Natural-language building specification.
        context:
            Optional dict with ``project_type``, ``climate_zone``,
            ``jurisdiction``, etc.

        Returns
        -------
        ParametricSpec
            Structured specification with all extracted parameters.
        """
        text = text.strip()
        if not text:
            return ParametricSpec(
                confidence=0.0,
                warnings=["Empty input provided."],
            )

        # Try LLM provider first
        spec = self._try_llm(text, context)
        if spec is not None:
            self._log_interaction(text, context, spec)
            return spec

        # Fall back to rule-based engine
        logger.debug("Using fallback regex engine for: %s", text[:80])
        spec = self._fallback.parse(text, context)
        self._log_interaction(text, context, spec)
        return spec

    def _log_interaction(
        self,
        text: str,
        context: dict[str, Any] | None,
        spec: ParametricSpec,
    ) -> None:
        """Auto-log the interaction if a collector is configured."""
        if self._collector is None:
            return
        try:
            self._collector.log_interaction(
                prompt=text,
                context=context,
                raw_output=None,
                parsed_spec=spec.model_dump() if hasattr(spec, "model_dump") else spec.__dict__,
                confidence=spec.confidence,
            )
        except Exception:
            logger.debug("Failed to log interaction for fine-tuning", exc_info=True)

    def _try_llm(
        self, text: str, context: dict[str, Any] | None,
    ) -> ParametricSpec | None:
        """Attempt to parse via the LLM provider.

        Returns *None* if the provider is unavailable or returns
        invalid output.
        """
        if not self._provider.is_available():
            logger.debug("LLM provider not available, will use fallback.")
            return None

        prompt = f"{_SYSTEM_PROMPT}\n\nDescription: {text}"
        if context:
            prompt += f"\n\nContext: {json.dumps(context)}"

        raw = self._provider.parse_with_llm(prompt)
        if raw is None:
            return None

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.debug("LLM returned invalid JSON: %s", raw[:200] if raw else "")
            return None

        try:
            spec = ParametricSpec(
                intent=data.get("intent", "create"),
                ifc_class=data.get("ifc_class", ""),
                name=data.get("name"),
                properties=data.get("properties", {}),
                materials=data.get("materials", []),
                performance=data.get("performance", {}),
                constraints=data.get("constraints", {}),
                compliance_codes=data.get("compliance_codes", []),
            )
        except Exception:
            logger.debug("Could not build ParametricSpec from LLM output", exc_info=True)
            return None

        # Apply context and scoring
        spec = apply_context(spec, context)
        spec.warnings = detect_ambiguities(spec, text)
        spec.confidence = min(compute_confidence(spec) + 0.10, 1.0)  # LLM bonus
        return spec
