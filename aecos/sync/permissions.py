"""Role-based access control for multi-user AEC OS projects."""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    ADMIN = "admin"
    DESIGNER = "designer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# Permission matrix: action -> set of roles allowed
_PERMISSIONS: dict[str, set[Role]] = {
    "create": {Role.ADMIN, Role.DESIGNER},
    "modify": {Role.ADMIN, Role.DESIGNER},
    "delete": {Role.ADMIN},
    "approve": {Role.ADMIN, Role.REVIEWER},
    "reject": {Role.ADMIN, Role.REVIEWER},
    "comment": {Role.ADMIN, Role.DESIGNER, Role.REVIEWER},
    "read": {Role.ADMIN, Role.DESIGNER, Role.REVIEWER, Role.VIEWER},
    "push": {Role.ADMIN, Role.DESIGNER},
    "pull": {Role.ADMIN, Role.DESIGNER, Role.REVIEWER, Role.VIEWER},
    "lock": {Role.ADMIN, Role.DESIGNER},
    "unlock": {Role.ADMIN, Role.DESIGNER},
    "config": {Role.ADMIN},
}


class PermissionError(Exception):
    """Raised when a user lacks permission for an action."""


class PermissionManager:
    """Manage role-based permissions stored in .aecos/permissions.json.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    """

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self._config_dir = self.project_root / ".aecos"
        self._config_path = self._config_dir / "permissions.json"
        self._users: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load permissions from disk."""
        if self._config_path.is_file():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                self._users = data.get("users", {})
            except (json.JSONDecodeError, OSError):
                logger.debug("Could not read permissions.json", exc_info=True)
                self._users = {}

    def _save(self) -> None:
        """Persist permissions to disk."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {"users": self._users}
        self._config_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8",
        )

    def set_role(self, user_id: str, role: Role | str) -> None:
        """Assign a role to a user."""
        if isinstance(role, str):
            role = Role(role)
        self._users[user_id] = role.value
        self._save()

    def get_role(self, user_id: str) -> Role:
        """Get a user's role. Defaults to viewer."""
        role_str = self._users.get(user_id, Role.VIEWER.value)
        try:
            return Role(role_str)
        except ValueError:
            return Role.VIEWER

    def remove_user(self, user_id: str) -> bool:
        """Remove a user from the permissions file."""
        if user_id in self._users:
            del self._users[user_id]
            self._save()
            return True
        return False

    def list_users(self) -> dict[str, str]:
        """Return all user-role mappings."""
        return dict(self._users)

    def check_permission(self, user_id: str, action: str) -> bool:
        """Check if user is allowed to perform action.

        Returns True if allowed, False otherwise.
        """
        role = self.get_role(user_id)
        allowed_roles = _PERMISSIONS.get(action, set())
        return role in allowed_roles

    def require_permission(self, user_id: str, action: str) -> None:
        """Raise PermissionError if user lacks permission."""
        if not self.check_permission(user_id, action):
            role = self.get_role(user_id)
            raise PermissionError(
                f"User '{user_id}' with role '{role.value}' "
                f"is not allowed to perform '{action}'."
            )
