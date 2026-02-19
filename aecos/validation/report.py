"""ValidationReport model and VALIDATION.md generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from aecos.validation.rules.base import ValidationIssue


class ValidationReport:
    """Complete validation report for an element."""

    def __init__(
        self,
        element_id: str = "",
        ifc_class: str = "",
        status: str = "passed",
        issues: list[ValidationIssue] | None = None,
        clash_results: list[Any] | None = None,
        validated_at: datetime | str | None = None,
    ) -> None:
        self.element_id = element_id
        self.ifc_class = ifc_class
        self.status = status
        self.issues = issues or []
        self.clash_results = clash_results or []
        if validated_at is None:
            self.validated_at = datetime.now(timezone.utc)
        elif isinstance(validated_at, str):
            self.validated_at = datetime.fromisoformat(validated_at)
        else:
            self.validated_at = validated_at

    def to_markdown(self) -> str:
        """Generate VALIDATION.md content."""
        lines: list[str] = []

        lines.append(f"# Validation Report — {self.element_id or 'Unknown'}")
        lines.append("")
        lines.append(f"**IFC Class:** `{self.ifc_class}`")
        lines.append(f"**Status:** {self.status.upper()}")
        lines.append(f"**Validated:** {self.validated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Summary counts
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        infos = sum(1 for i in self.issues if i.severity == "info")
        lines.append(f"**Summary:** {errors} errors, {warnings} warnings, {infos} info")
        lines.append("")

        # Issues table
        if self.issues:
            lines.append("## Issues")
            lines.append("")
            lines.append("| Severity | Rule | Message | Suggestion |")
            lines.append("|----------|------|---------|------------|")
            for issue in self.issues:
                msg = issue.message.replace("|", "\\|")
                sug = issue.suggestion.replace("|", "\\|")
                lines.append(
                    f"| {issue.severity.upper()} | {issue.rule_name} | {msg} | {sug} |"
                )
            lines.append("")

        # Clash results
        if self.clash_results:
            lines.append("## Clash Detection")
            lines.append("")
            lines.append(f"**Clashes found:** {len(self.clash_results)}")
            lines.append("")
            for clash in self.clash_results:
                if hasattr(clash, "message"):
                    lines.append(f"- {clash.message}")
                elif isinstance(clash, dict):
                    lines.append(f"- {clash.get('message', str(clash))}")
            lines.append("")

        if not self.issues and not self.clash_results:
            lines.append("No issues found. Element passes all validation checks.")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Return structured JSON report for audit trail."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Return dict representation."""
        return {
            "element_id": self.element_id,
            "ifc_class": self.ifc_class,
            "status": self.status,
            "validated_at": self.validated_at.isoformat(),
            "issues": [i.to_dict() for i in self.issues],
            "clash_results": [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in self.clash_results
            ],
        }
