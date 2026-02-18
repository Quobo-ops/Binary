"""SecurityReport model and SECURITY_REPORT.md generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single security finding."""

    severity: str = "info"  # critical, high, medium, low, info
    category: str = ""  # secret, permission, encryption, audit
    message: str = ""
    file_path: str = ""


class SecurityReport(BaseModel):
    """Complete security scan report."""

    scan_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    findings: list[Finding] = Field(default_factory=list)
    chain_valid: bool = True
    overall_status: str = "clean"  # clean, warning, critical

    def to_markdown(self) -> str:
        """Generate SECURITY_REPORT.md content."""
        lines = [
            "# Security Report",
            "",
            f"**Scan timestamp:** {self.scan_timestamp}",
            f"**Overall status:** {self.overall_status}",
            f"**Audit chain valid:** {'Yes' if self.chain_valid else 'NO — POSSIBLE TAMPERING'}",
            "",
        ]

        if not self.findings:
            lines.append("No findings.")
        else:
            lines.append(f"## Findings ({len(self.findings)})")
            lines.append("")

            for sev in ("critical", "high", "medium", "low", "info"):
                items = [f for f in self.findings if f.severity == sev]
                if not items:
                    continue
                lines.append(f"### {sev.upper()} ({len(items)})")
                lines.append("")
                for f in items:
                    path_part = f" — `{f.file_path}`" if f.file_path else ""
                    lines.append(f"- [{f.category}] {f.message}{path_part}")
                lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Return structured JSON report."""
        return json.dumps(self.model_dump(), indent=2)
