"""Security & Audit — Item 17.

Provides immutable hash-chained audit logging, content hashing,
file-level encryption, RBAC enforcement, vulnerability scanning,
and security report generation.
"""

from aecos.security.audit import AuditEntry, AuditLogger
from aecos.security.encryption import EncryptionManager
from aecos.security.hasher import Hasher
from aecos.security.policies import SecurityPolicy
from aecos.security.rbac import check_permission, require_role
from aecos.security.report import Finding, SecurityReport
from aecos.security.scanner import SecurityScanner

__all__ = [
    "AuditEntry",
    "AuditLogger",
    "EncryptionManager",
    "Finding",
    "Hasher",
    "SecurityPolicy",
    "SecurityReport",
    "SecurityScanner",
    "check_permission",
    "require_role",
]
