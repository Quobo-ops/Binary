"""Unified search across elements and templates.

Provides a single entry point for querying both project elements and
the template library simultaneously.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aecos.api.elements import list_elements
from aecos.models.element import Element
from aecos.templates.library import TemplateLibrary
from aecos.templates.registry import RegistryEntry

logger = logging.getLogger(__name__)


@dataclass
class SearchResults:
    """Combined results from element and template searches."""

    elements: list[Element] = field(default_factory=list)
    templates: list[RegistryEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.elements) + len(self.templates)


def unified_search(
    project_root: Path,
    library: TemplateLibrary | None = None,
    *,
    ifc_class: str | None = None,
    material: str | None = None,
    name: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    compliance_codes: str | None = None,
) -> SearchResults:
    """Search across both project elements and the template library.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    library:
        Optional :class:`TemplateLibrary` to search templates.
    ifc_class, material, name, region, keyword, compliance_codes:
        Optional filter criteria.

    Returns a :class:`SearchResults` with matched elements and templates.
    """
    results = SearchResults()

    # Search project elements
    elem_filters: dict[str, Any] = {}
    if ifc_class:
        elem_filters["ifc_class"] = ifc_class
    if material:
        elem_filters["material"] = material
    if name:
        elem_filters["name"] = name

    results.elements = list_elements(project_root, elem_filters)

    # Search template library
    if library is not None:
        tmpl_query: dict[str, object] = {}
        if ifc_class:
            tmpl_query["ifc_class"] = ifc_class
        if material:
            tmpl_query["material"] = material
        if region:
            tmpl_query["region"] = region
        if keyword:
            tmpl_query["keyword"] = keyword
        if compliance_codes:
            tmpl_query["compliance_codes"] = compliance_codes

        results.templates = library.search(tmpl_query)

    return results
