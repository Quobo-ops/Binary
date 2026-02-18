"""Domain Expansion — pluggable domain support for multiple AEC disciplines."""

from aecos.domains.base import DomainPlugin
from aecos.domains.registry import DomainRegistry

__all__ = [
    "DomainPlugin",
    "DomainRegistry",
]
