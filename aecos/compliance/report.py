"""ComplianceReport model and Markdown report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from aecos.compliance.rules import RuleResult


class ComplianceReport(BaseModel):
    """Full compliance-check report for a single element or spec."""

    element_id: str = ""
    ifc_class: str = ""
    status: str = "unknown"
    """Overall status: 'compliant', 'non_compliant', 'partial', 'unknown'."""

    results: list[RuleResult] = Field(default_factory=list)
    """Per-rule evaluation results."""

    suggested_fixes: list[str] = Field(default_factory=list)
    """Actionable suggestions for any violations."""

    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Timestamp of the compliance check."""

    def to_markdown(self) -> str:
        """Render the report as a Markdown document for COMPLIANCE.md."""
        lines: list[str] = []

        lines.append(f"# Compliance Report — {self.element_id or 'Unknown'}")
        lines.append("")
        lines.append(f"**IFC Class:** `{self.ifc_class}`")
        lines.append(f"**Status:** {self._status_badge()}")
        lines.append(f"**Checked:** {self.checked_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Summary counts
        passes = sum(1 for r in self.results if r.status == "pass")
        fails = sum(1 for r in self.results if r.status == "fail")
        skips = sum(1 for r in self.results if r.status in ("skip", "unknown"))
        lines.append(f"**Results:** {passes} passed, {fails} failed, {skips} skipped")
        lines.append("")

        # Detailed results
        if self.results:
            lines.append("## Rule Results")
            lines.append("")
            lines.append("| Status | Code | Section | Title | Detail |")
            lines.append("|--------|------|---------|-------|--------|")
            for r in self.results:
                icon = _status_icon(r.status)
                detail = r.message.replace("|", "\\|") if r.message else ""
                lines.append(
                    f"| {icon} | {r.code_name} | {r.section} | {r.title} | {detail} |"
                )
            lines.append("")

        # Citations for failures
        failures = [r for r in self.results if r.status == "fail"]
        if failures:
            lines.append("## Violations")
            lines.append("")
            for r in failures:
                lines.append(f"- **{r.code_name} {r.section}** — {r.title}")
                lines.append(f"  {r.message}")
                if r.citation:
                    lines.append(f"  *Citation:* {r.citation}")
                lines.append("")

        # Suggested fixes
        if self.suggested_fixes:
            lines.append("## Suggested Fixes")
            lines.append("")
            for fix in self.suggested_fixes:
                lines.append(f"- {fix}")
            lines.append("")

        return "\n".join(lines)

    def _status_badge(self) -> str:
        """Return a human-readable status string."""
        badges = {
            "compliant": "COMPLIANT",
            "non_compliant": "NON-COMPLIANT",
            "partial": "PARTIAL",
            "unknown": "UNKNOWN",
        }
        return badges.get(self.status, self.status.upper())


def _status_icon(status: str) -> str:
    """Return a text icon for a rule status."""
    return {
        "pass": "PASS",
        "fail": "FAIL",
        "skip": "SKIP",
        "unknown": "?",
    }.get(status, status)
