"""Tests for Item 14 — Domain Expansion.

Covers: DomainPlugin interface, DomainRegistry, all five domain plugins
(Structural, MEP, Interior, Sitework, Fire Protection), and injection
into compliance, parser, cost, and validation engines.

All tests run offline with zero network access.
"""

from __future__ import annotations

import pytest

from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.rules import Rule
from aecos.cost.engine import CostEngine
from aecos.cost.seed_data import SEED_PRICING
from aecos.domains.base import DomainPlugin
from aecos.domains.fire_protection import FireProtectionDomain
from aecos.domains.interior import InteriorDomain
from aecos.domains.mep import MEPDomain
from aecos.domains.registry import DomainRegistry
from aecos.domains.sitework import SiteworkDomain
from aecos.domains.structural import StructuralDomain
from aecos.nlp.parser import NLParser
from aecos.nlp.properties import _IFC_CLASS_MAP
from aecos.nlp.providers.fallback import FallbackProvider
from aecos.validation.validator import Validator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


ALL_DOMAIN_CLASSES = [
    StructuralDomain,
    MEPDomain,
    InteriorDomain,
    SiteworkDomain,
    FireProtectionDomain,
]


@pytest.fixture
def registry() -> DomainRegistry:
    """Registry with auto-discovered domains."""
    reg = DomainRegistry()
    reg.auto_discover()
    return reg


@pytest.fixture
def compliance_engine() -> ComplianceEngine:
    """Compliance engine with in-memory database."""
    return ComplianceEngine(":memory:")


@pytest.fixture
def parser() -> NLParser:
    """NL parser with fallback provider."""
    return NLParser(provider=FallbackProvider())


@pytest.fixture
def validator() -> Validator:
    return Validator()


# ---------------------------------------------------------------------------
# DomainPlugin ABC
# ---------------------------------------------------------------------------


class TestDomainPluginInterface:
    """All domain plugins must implement the DomainPlugin interface."""

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_is_domain_plugin(self, domain_cls: type) -> None:
        domain = domain_cls()
        assert isinstance(domain, DomainPlugin)

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_name_is_string(self, domain_cls: type) -> None:
        domain = domain_cls()
        assert isinstance(domain.name, str)
        assert len(domain.name) > 0

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_description_is_string(self, domain_cls: type) -> None:
        domain = domain_cls()
        assert isinstance(domain.description, str)
        assert len(domain.description) > 0

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_ifc_classes_non_empty(self, domain_cls: type) -> None:
        domain = domain_cls()
        classes = domain.ifc_classes
        assert isinstance(classes, list)
        assert len(classes) > 0
        for cls in classes:
            assert cls.startswith("Ifc")

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_register_templates(self, domain_cls: type) -> None:
        domain = domain_cls()
        templates = domain.register_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 4
        for t in templates:
            assert "template_id" in t
            assert "ifc_class" in t
            assert "name" in t
            assert "materials" in t

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_register_compliance_rules(self, domain_cls: type) -> None:
        domain = domain_cls()
        rules = domain.register_compliance_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 4
        for r in rules:
            assert "code_name" in r
            assert "section" in r
            assert "title" in r
            assert "ifc_classes" in r
            assert "check_type" in r

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_register_parser_patterns(self, domain_cls: type) -> None:
        domain = domain_cls()
        patterns = domain.register_parser_patterns()
        assert isinstance(patterns, dict)
        assert len(patterns) >= 4
        for keyword, ifc_class in patterns.items():
            assert isinstance(keyword, str)
            assert ifc_class.startswith("Ifc")

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_register_cost_data(self, domain_cls: type) -> None:
        domain = domain_cls()
        entries = domain.register_cost_data()
        assert isinstance(entries, list)
        assert len(entries) >= 4
        for e in entries:
            assert "material" in e
            assert "ifc_class" in e
            assert "material_cost_per_unit" in e
            assert "labor_cost_per_unit" in e
            assert "unit_type" in e

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_register_validation_rules(self, domain_cls: type) -> None:
        domain = domain_cls()
        rules = domain.register_validation_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 2

    @pytest.mark.parametrize("domain_cls", ALL_DOMAIN_CLASSES)
    def test_get_builder_config(self, domain_cls: type) -> None:
        domain = domain_cls()
        for ifc_class in domain.ifc_classes:
            config = domain.get_builder_config(ifc_class)
            assert isinstance(config, dict)


# ---------------------------------------------------------------------------
# DomainRegistry
# ---------------------------------------------------------------------------


class TestDomainRegistry:
    def test_auto_discover_loads_five_domains(self, registry: DomainRegistry) -> None:
        domains = registry.list_domains()
        assert len(domains) == 5

    def test_auto_discover_names(self, registry: DomainRegistry) -> None:
        names = {d.name for d in registry.list_domains()}
        assert names == {"structural", "mep", "interior", "sitework", "fire_protection"}

    def test_get_domain_by_name(self, registry: DomainRegistry) -> None:
        assert registry.get_domain("structural") is not None
        assert registry.get_domain("mep") is not None
        assert registry.get_domain("nonexistent") is None

    def test_get_domain_for_ifc_class(self, registry: DomainRegistry) -> None:
        beam_domain = registry.get_domain_for_ifc_class("IfcBeam")
        assert beam_domain is not None
        assert beam_domain.name == "structural"

        duct_domain = registry.get_domain_for_ifc_class("IfcDuctSegment")
        assert duct_domain is not None
        assert duct_domain.name == "mep"

    def test_get_domain_for_unknown_class(self, registry: DomainRegistry) -> None:
        assert registry.get_domain_for_ifc_class("IfcUnknown") is None

    def test_manual_register(self) -> None:
        reg = DomainRegistry()
        domain = StructuralDomain()
        reg.register(domain)
        assert reg.get_domain("structural") is domain

    def test_apply_all_returns_stats(self, registry: DomainRegistry) -> None:
        engine = ComplianceEngine(":memory:")
        parser = NLParser(provider=FallbackProvider())
        cost = CostEngine()
        val = Validator()

        stats = registry.apply_all(
            compliance_engine=engine,
            parser=parser,
            cost_engine=cost,
            validator=val,
        )

        assert stats["rules"] > 0
        assert stats["parser_patterns"] > 0
        assert stats["cost_entries"] > 0
        assert stats["validation_rules"] > 0


# ---------------------------------------------------------------------------
# Compliance rule injection
# ---------------------------------------------------------------------------


class TestComplianceInjection:
    def test_structural_rules_injected(
        self, registry: DomainRegistry, compliance_engine: ComplianceEngine
    ) -> None:
        initial_count = len(compliance_engine.get_rules())
        registry.apply_all(compliance_engine=compliance_engine)
        final_count = len(compliance_engine.get_rules())
        assert final_count > initial_count

    def test_beam_rules_present(
        self, registry: DomainRegistry, compliance_engine: ComplianceEngine
    ) -> None:
        registry.apply_all(compliance_engine=compliance_engine)
        beam_rules = compliance_engine.get_rules(ifc_class="IfcBeam")
        assert len(beam_rules) > 0

    def test_injected_rules_are_valid(
        self, registry: DomainRegistry, compliance_engine: ComplianceEngine
    ) -> None:
        registry.apply_all(compliance_engine=compliance_engine)
        all_rules = compliance_engine.get_rules()
        for rule in all_rules:
            assert isinstance(rule, Rule)
            assert rule.code_name != ""
            assert rule.section != ""


# ---------------------------------------------------------------------------
# Parser pattern injection
# ---------------------------------------------------------------------------


class TestParserInjection:
    def test_domain_patterns_injected(self, registry: DomainRegistry) -> None:
        parser = NLParser(provider=FallbackProvider())
        registry.apply_all(parser=parser)

        # Structural patterns
        assert _IFC_CLASS_MAP.get("footing") == "IfcFooting"
        assert _IFC_CLASS_MAP.get("pile") == "IfcPile"

    def test_mep_patterns_injected(self, registry: DomainRegistry) -> None:
        parser = NLParser(provider=FallbackProvider())
        registry.apply_all(parser=parser)

        assert _IFC_CLASS_MAP.get("duct") == "IfcDuctSegment"
        assert _IFC_CLASS_MAP.get("pipe") == "IfcPipeSegment"

    def test_parser_recognizes_domain_keywords(self, registry: DomainRegistry) -> None:
        parser = NLParser(provider=FallbackProvider())
        registry.apply_all(parser=parser)

        spec = parser.parse("concrete footing 1200mm wide")
        assert spec.ifc_class == "IfcFooting"


# ---------------------------------------------------------------------------
# Cost data injection
# ---------------------------------------------------------------------------


class TestCostInjection:
    def test_cost_entries_injected(self, registry: DomainRegistry) -> None:
        cost = CostEngine()
        registry.apply_all(cost_engine=cost)

        # Check that structural entries are in SEED_PRICING
        assert ("steel", "IfcBeam") in SEED_PRICING
        assert ("concrete", "IfcColumn") in SEED_PRICING

    def test_mep_cost_entries(self, registry: DomainRegistry) -> None:
        cost = CostEngine()
        registry.apply_all(cost_engine=cost)

        assert ("steel", "IfcDuctSegment") in SEED_PRICING or \
               ("galvanized steel", "IfcDuctSegment") in SEED_PRICING


# ---------------------------------------------------------------------------
# Validation rule injection
# ---------------------------------------------------------------------------


class TestValidationInjection:
    def test_validation_rules_injected(self, registry: DomainRegistry) -> None:
        val = Validator()
        initial = len(val.rules)
        registry.apply_all(validator=val)
        assert len(val.rules) > initial

    def test_structural_rules_present(self, registry: DomainRegistry) -> None:
        val = Validator()
        registry.apply_all(validator=val)
        rule_names = [r.name for r in val.rules]
        assert "structural_load_path" in rule_names
        assert "structural_profile_spec" in rule_names


# ---------------------------------------------------------------------------
# Individual domain specifics
# ---------------------------------------------------------------------------


class TestStructuralDomain:
    def test_name(self) -> None:
        d = StructuralDomain()
        assert d.name == "structural"

    def test_ifc_classes(self) -> None:
        d = StructuralDomain()
        assert "IfcBeam" in d.ifc_classes
        assert "IfcColumn" in d.ifc_classes
        assert "IfcSlab" in d.ifc_classes

    def test_templates_count(self) -> None:
        d = StructuralDomain()
        assert len(d.register_templates()) >= 10

    def test_compliance_rules_count(self) -> None:
        d = StructuralDomain()
        assert len(d.register_compliance_rules()) >= 8


class TestMEPDomain:
    def test_name(self) -> None:
        d = MEPDomain()
        assert d.name == "mep"

    def test_ifc_classes(self) -> None:
        d = MEPDomain()
        assert "IfcDuctSegment" in d.ifc_classes
        assert "IfcPipeSegment" in d.ifc_classes


class TestInteriorDomain:
    def test_name(self) -> None:
        d = InteriorDomain()
        assert d.name == "interior"

    def test_ifc_classes(self) -> None:
        d = InteriorDomain()
        assert "IfcFurniture" in d.ifc_classes or "IfcCovering" in d.ifc_classes


class TestSiteworkDomain:
    def test_name(self) -> None:
        d = SiteworkDomain()
        assert d.name == "sitework"


class TestFireProtectionDomain:
    def test_name(self) -> None:
        d = FireProtectionDomain()
        assert d.name == "fire_protection"

    def test_nfpa_rules(self) -> None:
        d = FireProtectionDomain()
        rules = d.register_compliance_rules()
        code_names = {r["code_name"] for r in rules}
        assert any("NFPA" in cn for cn in code_names)
