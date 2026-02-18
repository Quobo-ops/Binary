"""Abstract DomainPlugin interface.

Every domain plugin must implement this interface to register its
templates, compliance rules, parser patterns, cost data, and validation
rules into the core AEC OS engines.
"""

from __future__ import annotations

import abc
from typing import Any


class DomainPlugin(abc.ABC):
    """Base class for all domain plugins."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short domain identifier (e.g. 'structural', 'mep')."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Human-readable description of the domain."""

    @property
    @abc.abstractmethod
    def ifc_classes(self) -> list[str]:
        """IFC types this domain handles."""

    @abc.abstractmethod
    def register_templates(self) -> list[dict[str, Any]]:
        """Return template definitions for the template library.

        Each dict should contain at minimum:
        - template_id: str
        - ifc_class: str
        - name: str
        - description: str
        - properties: dict (default dimensions/properties)
        - materials: list[str]
        - tags: dict (TemplateTags-compatible)
        """

    @abc.abstractmethod
    def register_compliance_rules(self) -> list[dict[str, Any]]:
        """Return Rule-compatible dicts for the compliance database.

        Each dict should have: code_name, section, title, ifc_classes,
        check_type, property_path, check_value, region, citation,
        effective_date.
        """

    @abc.abstractmethod
    def register_parser_patterns(self) -> dict[str, str]:
        """Return keyword -> IFC class mappings for the NLP FallbackProvider.

        Example: {"beam": "IfcBeam", "column": "IfcColumn"}
        """

    @abc.abstractmethod
    def register_cost_data(self) -> list[dict[str, Any]]:
        """Return pricing entries for the cost engine.

        Each dict: material, ifc_class, material_cost_per_unit,
        labor_cost_per_unit, unit_type, source.
        """

    @abc.abstractmethod
    def register_validation_rules(self) -> list[Any]:
        """Return ValidationRule instances for the validator."""

    @abc.abstractmethod
    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        """Return default properties for generation of the given IFC class."""
