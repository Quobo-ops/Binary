"""DomainRegistry — discover, register, and query domain plugins."""

from __future__ import annotations

import logging
from typing import Any

from aecos.domains.base import DomainPlugin

logger = logging.getLogger(__name__)


class DomainRegistry:
    """Central registry for domain plugins.

    Manages discovery, registration, and injection of domain-specific
    data into the core AEC OS engines.
    """

    def __init__(self) -> None:
        self._domains: dict[str, DomainPlugin] = {}
        self._ifc_class_map: dict[str, str] = {}  # ifc_class -> domain_name

    def register(self, domain: DomainPlugin) -> None:
        """Add a domain to the registry."""
        self._domains[domain.name] = domain
        for ifc_class in domain.ifc_classes:
            self._ifc_class_map[ifc_class] = domain.name
        logger.info("Registered domain: %s", domain.name)

    def auto_discover(self) -> None:
        """Load all built-in domains."""
        from aecos.domains.fire_protection import FireProtectionDomain
        from aecos.domains.interior import InteriorDomain
        from aecos.domains.mep import MEPDomain
        from aecos.domains.sitework import SiteworkDomain
        from aecos.domains.structural import StructuralDomain

        for domain_cls in [
            StructuralDomain,
            MEPDomain,
            InteriorDomain,
            SiteworkDomain,
            FireProtectionDomain,
        ]:
            domain = domain_cls()
            self.register(domain)

    def get_domain(self, name: str) -> DomainPlugin | None:
        """Get a domain by name."""
        return self._domains.get(name)

    def get_domain_for_ifc_class(self, ifc_class: str) -> DomainPlugin | None:
        """Get the domain that handles a given IFC class."""
        domain_name = self._ifc_class_map.get(ifc_class)
        if domain_name is None:
            return None
        return self._domains.get(domain_name)

    def list_domains(self) -> list[DomainPlugin]:
        """Return all registered domains."""
        return list(self._domains.values())

    def apply_all(
        self,
        *,
        compliance_engine: Any = None,
        parser: Any = None,
        cost_engine: Any = None,
        validator: Any = None,
    ) -> dict[str, int]:
        """Inject all domain data into the core engines.

        Returns a summary dict with counts of injected items.
        """
        stats: dict[str, int] = {
            "rules": 0,
            "parser_patterns": 0,
            "cost_entries": 0,
            "validation_rules": 0,
        }

        for domain in self._domains.values():
            # Inject compliance rules
            if compliance_engine is not None:
                try:
                    from aecos.compliance.rules import Rule

                    for rule_dict in domain.register_compliance_rules():
                        rule = Rule(**rule_dict)
                        compliance_engine.add_rule(rule)
                        stats["rules"] += 1
                except Exception:
                    logger.debug(
                        "Failed to inject compliance rules for %s",
                        domain.name,
                        exc_info=True,
                    )

            # Inject parser patterns
            if parser is not None:
                try:
                    patterns = domain.register_parser_patterns()
                    _inject_parser_patterns(parser, patterns)
                    stats["parser_patterns"] += len(patterns)
                except Exception:
                    logger.debug(
                        "Failed to inject parser patterns for %s",
                        domain.name,
                        exc_info=True,
                    )

            # Inject cost data
            if cost_engine is not None:
                try:
                    cost_entries = domain.register_cost_data()
                    _inject_cost_data(cost_engine, cost_entries)
                    stats["cost_entries"] += len(cost_entries)
                except Exception:
                    logger.debug(
                        "Failed to inject cost data for %s",
                        domain.name,
                        exc_info=True,
                    )

            # Inject validation rules
            if validator is not None:
                try:
                    v_rules = domain.register_validation_rules()
                    for v_rule in v_rules:
                        validator.add_rule(v_rule)
                        stats["validation_rules"] += 1
                except Exception:
                    logger.debug(
                        "Failed to inject validation rules for %s",
                        domain.name,
                        exc_info=True,
                    )

        logger.info(
            "Domain injection complete: %d rules, %d parser patterns, "
            "%d cost entries, %d validation rules",
            stats["rules"],
            stats["parser_patterns"],
            stats["cost_entries"],
            stats["validation_rules"],
        )
        return stats


def _inject_parser_patterns(parser: Any, patterns: dict[str, str]) -> None:
    """Inject keyword->IFC class mappings into the NLP parser's fallback."""
    from aecos.nlp.properties import _IFC_CLASS_MAP

    for keyword, ifc_class in patterns.items():
        _IFC_CLASS_MAP[keyword.lower()] = ifc_class


def _inject_cost_data(cost_engine: Any, entries: list[dict[str, Any]]) -> None:
    """Inject pricing entries into the cost engine's provider."""
    from aecos.cost.seed_data import SEED_PRICING

    for entry in entries:
        key = (entry["material"].lower(), entry["ifc_class"])
        SEED_PRICING[key] = {
            "material_cost_per_unit": entry["material_cost_per_unit"],
            "labor_cost_per_unit": entry["labor_cost_per_unit"],
            "unit_type": entry["unit_type"],
            "source": entry.get("source", "Domain plugin"),
        }
