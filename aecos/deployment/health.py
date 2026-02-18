"""HealthChecker — validates a running installation."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CheckResult(BaseModel):
    """Result of a single health check."""

    name: str = ""
    passed: bool = True
    message: str = ""
    severity: str = "info"  # info, warning, critical


class HealthReport(BaseModel):
    """Aggregate health report."""

    status: str = "healthy"  # healthy, degraded, unhealthy
    checks: list[CheckResult] = Field(default_factory=list)


class HealthChecker:
    """Validate an AEC OS installation."""

    def check(self, project_path: str | Path) -> HealthReport:
        """Run all health checks and return a report."""
        root = Path(project_path)
        checks: list[CheckResult] = []

        # 1. Python version
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        checks.append(CheckResult(
            name="python_version",
            passed=sys.version_info >= (3, 11),
            message=f"Python {py_ver}",
            severity="critical" if sys.version_info < (3, 11) else "info",
        ))

        # 2. Git repo valid
        git_dir = root / ".git"
        checks.append(CheckResult(
            name="git_repo",
            passed=git_dir.is_dir(),
            message="Git repository found" if git_dir.is_dir() else "No git repository",
            severity="warning" if not git_dir.is_dir() else "info",
        ))

        # 3. Elements directory
        elems = root / "elements"
        checks.append(CheckResult(
            name="elements_dir",
            passed=elems.is_dir(),
            message="Elements directory exists" if elems.is_dir() else "No elements directory",
            severity="warning" if not elems.is_dir() else "info",
        ))

        # 4. Templates directory
        tmpls = root / "templates"
        checks.append(CheckResult(
            name="templates_dir",
            passed=tmpls.is_dir(),
            message="Templates directory exists" if tmpls.is_dir() else "No templates directory",
            severity="warning" if not tmpls.is_dir() else "info",
        ))

        # 5. Compliance DB (check if module is importable — engine uses :memory: by default)
        try:
            from aecos.compliance.engine import ComplianceEngine
            checks.append(CheckResult(
                name="compliance_engine",
                passed=True,
                message="Compliance engine available",
            ))
        except Exception as exc:
            checks.append(CheckResult(
                name="compliance_engine",
                passed=False,
                message=f"Compliance engine unavailable: {exc}",
                severity="critical",
            ))

        # 6. Check module importability
        module_checks = self.check_all_modules()
        checks.extend(module_checks)

        # Determine overall status
        critical_fail = any(c.severity == "critical" and not c.passed for c in checks)
        warning_fail = any(c.severity == "warning" and not c.passed for c in checks)

        if critical_fail:
            status = "unhealthy"
        elif warning_fail:
            status = "degraded"
        else:
            status = "healthy"

        return HealthReport(status=status, checks=checks)

    def check_all_modules(self) -> list[CheckResult]:
        """Verify each aecos subpackage is importable."""
        results: list[CheckResult] = []

        modules = [
            "aecos.extraction",
            "aecos.templates",
            "aecos.metadata",
            "aecos.vcs",
            "aecos.api",
            "aecos.nlp",
            "aecos.compliance",
            "aecos.generation",
            "aecos.validation",
            "aecos.cost",
            "aecos.visualization",
            "aecos.sync",
            "aecos.finetune",
            "aecos.domains",
            "aecos.regulatory",
            "aecos.collaboration",
            "aecos.security",
            "aecos.deployment",
            "aecos.analytics",
        ]

        for mod in modules:
            try:
                importlib.import_module(mod)
                results.append(CheckResult(
                    name=f"module_{mod.split('.')[-1]}",
                    passed=True,
                    message=f"{mod} importable",
                ))
            except Exception as exc:
                results.append(CheckResult(
                    name=f"module_{mod.split('.')[-1]}",
                    passed=False,
                    message=f"{mod} failed: {exc}",
                    severity="critical",
                ))

        return results
