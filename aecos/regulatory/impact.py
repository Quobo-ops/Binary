"""ImpactAnalyzer — finds affected templates and elements after rule changes."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aecos.regulatory.differ import RuleDiffResult

logger = logging.getLogger(__name__)


class ImpactReport(BaseModel):
    """Report of which templates and elements are affected by rule changes."""

    affected_templates: list[str] = Field(default_factory=list)
    affected_elements: list[str] = Field(default_factory=list)
    re_validation_needed: list[str] = Field(default_factory=list)
    affected_ifc_classes: list[str] = Field(default_factory=list)
    total_affected: int = 0

    def summary(self) -> str:
        return (
            f"Affected: {len(self.affected_templates)} templates, "
            f"{len(self.affected_elements)} elements, "
            f"{len(self.re_validation_needed)} need re-validation."
        )


class ImpactAnalyzer:
    """Analyze the impact of rule changes on templates and elements."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root

    def analyze(
        self,
        diff: RuleDiffResult,
        library_path: Path | None = None,
    ) -> ImpactReport:
        """Analyze which templates and elements are affected by rule changes.

        Parameters
        ----------
        diff:
            The rule diff result to analyze.
        library_path:
            Path to the template library directory.
        """
        report = ImpactReport()

        if not diff.has_changes:
            return report

        # Collect all affected IFC classes from changed rules
        affected_classes: set[str] = set()
        for rule in diff.added:
            affected_classes.update(rule.ifc_classes)
        for _old_rule, new_rule in diff.modified:
            affected_classes.update(new_rule.ifc_classes)
        for rule in diff.removed:
            affected_classes.update(rule.ifc_classes)

        report.affected_ifc_classes = sorted(affected_classes)

        # Scan template library
        if library_path and library_path.is_dir():
            report.affected_templates = self._scan_templates(library_path, affected_classes)

        # Scan elements
        if self.project_root:
            elements_dir = self.project_root / "elements"
            if elements_dir.is_dir():
                report.affected_elements = self._scan_elements(elements_dir, affected_classes)

        report.re_validation_needed = report.affected_templates + report.affected_elements
        report.total_affected = len(report.affected_templates) + len(report.affected_elements)

        logger.info("Impact analysis: %s", report.summary())
        return report

    @staticmethod
    def _scan_templates(library_path: Path, affected_classes: set[str]) -> list[str]:
        """Scan template folders for those matching affected IFC classes."""
        affected: list[str] = []
        for folder in library_path.iterdir():
            if not folder.is_dir() or not folder.name.startswith("template_"):
                continue
            meta_path = folder / "metadata.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                ifc_class = meta.get("IFCClass", "")
                if ifc_class in affected_classes:
                    affected.append(folder.name)
            except (json.JSONDecodeError, OSError):
                pass
        return affected

    @staticmethod
    def _scan_elements(elements_dir: Path, affected_classes: set[str]) -> list[str]:
        """Scan element folders for those matching affected IFC classes."""
        affected: list[str] = []
        for folder in elements_dir.iterdir():
            if not folder.is_dir() or not folder.name.startswith("element_"):
                continue
            meta_path = folder / "metadata.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                ifc_class = meta.get("IFCClass", "")
                if ifc_class in affected_classes:
                    affected.append(folder.name)
            except (json.JSONDecodeError, OSError):
                pass
        return affected
