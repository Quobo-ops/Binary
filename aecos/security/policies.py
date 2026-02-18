"""SecurityPolicy — configurable rules and thresholds."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityPolicy(BaseModel):
    """Configurable security policy model."""

    max_failed_logins: int = 5
    password_min_length: int = 12
    key_rotation_days: int = 90
    audit_retention_days: int = 365
    require_encryption_for: list[str] = Field(
        default_factory=lambda: [".env", ".key", "credentials.json"],
    )
    scan_patterns: list[str] = Field(
        default_factory=lambda: [".env", ".json", ".py", ".toml", ".yml", ".yaml"],
    )
    secret_regex_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)(aws[_\-]?access[_\-]?key[_\-]?id)\s*[:=]\s*['\"]?[A-Z0-9]{20}",
            r"(?i)(aws[_\-]?secret[_\-]?access[_\-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}",
            r"(?i)(slack[_\-]?token|slack[_\-]?webhook)\s*[:=]\s*['\"]?xox[bpors]-[A-Za-z0-9\-]+",
            r"(?i)(api[_\-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}",
            r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}",
            r"(?i)(secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
            r"(?i)ghp_[A-Za-z0-9]{36}",
            r"(?i)sk-[A-Za-z0-9]{32,}",
        ],
    )
    role_permissions: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "admin": [
                "create", "modify", "delete", "approve", "reject", "comment",
                "read", "push", "pull", "lock", "unlock", "config",
                "audit_export", "key_manage", "encrypt", "decrypt",
            ],
            "designer": [
                "create", "modify", "approve", "comment", "read",
                "push", "pull", "lock", "unlock",
            ],
            "reviewer": [
                "read", "pull", "approve", "reject", "comment",
            ],
            "viewer": [
                "read", "pull",
            ],
            "auditor": [
                "read", "pull", "audit_export",
            ],
        },
    )
