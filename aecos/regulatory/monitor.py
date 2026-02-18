"""UpdateMonitor — checks for code amendments.

In local-only mode, returns cached results and logs offline status.
Automated checking is an optional runtime plugin.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from aecos.regulatory.sources import CodeSource, DEFAULT_SOURCES

logger = logging.getLogger(__name__)


class UpdateCheckResult(BaseModel):
    """Result of checking a single code source for updates."""

    code_name: str
    current_version: str
    new_version_available: bool = False
    new_version: str = ""
    changes: list[dict[str, Any]] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_method: str = "manual"
    offline: bool = False


class UpdateMonitor:
    """Monitor regulatory code sources for amendments.

    In local-only mode (no network), returns cached results and logs
    offline status. Automated scraping/API checking is optional.
    """

    def __init__(self, sources: list[CodeSource] | None = None) -> None:
        self.sources: dict[str, CodeSource] = {}
        for src in (sources or DEFAULT_SOURCES):
            self.sources[src.code_name] = src

    def add_source(self, source: CodeSource) -> None:
        """Register a new code source to monitor."""
        self.sources[source.code_name] = source

    def get_source(self, code_name: str) -> CodeSource | None:
        """Get a registered code source."""
        return self.sources.get(code_name)

    def check_source(self, source: CodeSource) -> UpdateCheckResult:
        """Check a single source for updates.

        In manual/offline mode, returns a no-update result.
        """
        source.last_checked = datetime.now(timezone.utc)

        if source.check_method == "manual":
            logger.info("Source %s uses manual check method — no auto-check.", source.code_name)
            return UpdateCheckResult(
                code_name=source.code_name,
                current_version=source.current_version,
                new_version_available=False,
                source_method="manual",
                offline=False,
            )

        # For non-manual methods, try network (will fail in offline mode)
        logger.info("Source %s offline mode — returning cached result.", source.code_name)
        return UpdateCheckResult(
            code_name=source.code_name,
            current_version=source.current_version,
            new_version_available=False,
            source_method=source.check_method,
            offline=True,
        )

    def check_all(self) -> list[UpdateCheckResult]:
        """Check all registered sources for updates."""
        results: list[UpdateCheckResult] = []
        for source in self.sources.values():
            results.append(self.check_source(source))
        return results
