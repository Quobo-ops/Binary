"""CodeSource model — registry of regulatory code sources."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class CodeSource(BaseModel):
    """Represents a regulatory code source to monitor for updates."""

    code_name: str
    """Code identifier: 'IBC2024', 'CBC2025', 'Title-24', etc."""

    current_version: str = "1.0.0"
    """Currently tracked version of this code."""

    check_url: Optional[str] = None
    """Optional URL for automated checking (not used in local-only mode)."""

    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Timestamp of last check."""

    check_method: str = "manual"
    """How to check: 'manual' (always available), 'api', 'scrape'."""

    description: str = ""
    """Human-readable description of this code source."""


# Built-in code sources — these are the codes AEC OS tracks by default.
DEFAULT_SOURCES: list[CodeSource] = [
    CodeSource(
        code_name="IBC2024",
        current_version="2024.0",
        check_method="manual",
        description="International Building Code 2024 edition",
    ),
    CodeSource(
        code_name="CBC2025",
        current_version="2025.0",
        check_method="manual",
        description="California Building Code 2025 edition",
    ),
    CodeSource(
        code_name="Title-24",
        current_version="2022.1",
        check_method="manual",
        description="California Title 24 Part 6 Energy Code",
    ),
    CodeSource(
        code_name="ADA2010",
        current_version="2010.0",
        check_method="manual",
        description="Americans with Disabilities Act 2010 Standards",
    ),
    CodeSource(
        code_name="ASCE7-22",
        current_version="2022.0",
        check_method="manual",
        description="ASCE 7-22 Minimum Design Loads",
    ),
    CodeSource(
        code_name="NFPA13",
        current_version="2022.0",
        check_method="manual",
        description="NFPA 13 Standard for Installation of Sprinkler Systems",
    ),
]
