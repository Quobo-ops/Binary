"""SecurityScanner — vulnerability and anomaly detection."""

from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path
from typing import Any

from aecos.security.audit import AuditLogger
from aecos.security.policies import SecurityPolicy
from aecos.security.report import Finding, SecurityReport

logger = logging.getLogger(__name__)


class SecurityScanner:
    """Scan a project for secrets, permission anomalies, and audit integrity.

    Parameters
    ----------
    policy:
        Security policy with patterns and thresholds.
    audit_logger:
        Optional AuditLogger for chain integrity checks.
    """

    def __init__(
        self,
        policy: SecurityPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.policy = policy or SecurityPolicy()
        self.audit_logger = audit_logger

    def scan_secrets(self, project_path: str | Path) -> list[Finding]:
        """Scan for files potentially containing secrets."""
        findings: list[Finding] = []
        root = Path(project_path)

        patterns = [re.compile(p) for p in self.policy.secret_regex_patterns]

        for ext in self.policy.scan_patterns:
            for fpath in root.rglob(f"*{ext}"):
                if not fpath.is_file():
                    continue
                # Skip .git internals
                try:
                    rel = fpath.relative_to(root).as_posix()
                except ValueError:
                    rel = str(fpath)
                if ".git/" in rel or "__pycache__/" in rel:
                    continue

                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                for pat in patterns:
                    matches = pat.findall(content)
                    if matches:
                        findings.append(Finding(
                            severity="high",
                            category="secret",
                            message=f"Potential secret found matching pattern in {rel}",
                            file_path=rel,
                        ))
                        break  # one finding per file is enough

        return findings

    def scan_permissions(self, project_path: str | Path) -> list[Finding]:
        """Scan for permission anomalies."""
        findings: list[Finding] = []
        root = Path(project_path)

        sensitive_extensions = {".env", ".key", ".pem", ".p12"}

        for fpath in root.rglob("*"):
            if not fpath.is_file():
                continue
            try:
                rel = fpath.relative_to(root).as_posix()
            except ValueError:
                rel = str(fpath)
            if ".git/" in rel or "__pycache__/" in rel:
                continue

            # Check world-writable
            try:
                mode = fpath.stat().st_mode
                if mode & stat.S_IWOTH:
                    findings.append(Finding(
                        severity="medium",
                        category="permission",
                        message=f"World-writable file: {rel}",
                        file_path=rel,
                    ))
            except OSError:
                pass

            # Unencrypted sensitive files
            if fpath.suffix in sensitive_extensions:
                # A very simplistic check: if the file is readable as text, it's
                # likely unencrypted.
                try:
                    content = fpath.read_bytes()[:64]
                    if content and all(32 <= b < 127 or b in (9, 10, 13) for b in content):
                        findings.append(Finding(
                            severity="medium",
                            category="encryption",
                            message=f"Potentially unencrypted sensitive file: {rel}",
                            file_path=rel,
                        ))
                except OSError:
                    pass

        return findings

    def scan_audit_integrity(self) -> list[Finding]:
        """Verify audit hash chain and detect gaps."""
        findings: list[Finding] = []

        if self.audit_logger is None:
            findings.append(Finding(
                severity="info",
                category="audit",
                message="No audit logger configured — chain check skipped",
                file_path="",
            ))
            return findings

        if not self.audit_logger.verify_chain():
            findings.append(Finding(
                severity="critical",
                category="audit",
                message="Audit hash chain integrity check FAILED — possible tampering",
                file_path="",
            ))
        else:
            findings.append(Finding(
                severity="info",
                category="audit",
                message="Audit hash chain integrity verified",
                file_path="",
            ))

        return findings

    def scan_all(self, project_path: str | Path) -> SecurityReport:
        """Full security scan returning a comprehensive report."""
        all_findings: list[Finding] = []

        all_findings.extend(self.scan_secrets(project_path))
        all_findings.extend(self.scan_permissions(project_path))
        all_findings.extend(self.scan_audit_integrity())

        chain_valid = True
        if self.audit_logger:
            chain_valid = self.audit_logger.verify_chain()

        critical = sum(1 for f in all_findings if f.severity == "critical")
        high = sum(1 for f in all_findings if f.severity == "high")

        if critical > 0:
            status = "critical"
        elif high > 0:
            status = "warning"
        else:
            status = "clean"

        return SecurityReport(
            findings=all_findings,
            chain_valid=chain_valid,
            overall_status=status,
        )
