"""RBAC enforcement — extends sync/permissions.py with security roles."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from aecos.security.policies import SecurityPolicy

logger = logging.getLogger(__name__)

_default_policy = SecurityPolicy()


def check_permission(
    user: str,
    role: str,
    action: str,
    resource: str = "",
    policy: SecurityPolicy | None = None,
) -> bool:
    """Check whether *role* is allowed to perform *action*.

    Uses the policy's ``role_permissions`` matrix.
    """
    pol = policy or _default_policy
    allowed = pol.role_permissions.get(role, [])
    return action in allowed


def require_role(*roles: str) -> Callable[..., Any]:
    """Decorator that enforces role membership.

    The decorated function must accept ``user`` and ``role`` keyword
    arguments (or positional args — the decorator inspects both).

    Usage::

        @require_role("admin", "designer")
        def create_element(user, role, ...):
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            role = kwargs.get("role", "")
            if not role and len(args) >= 2:
                role = args[1]
            if role not in roles:
                raise PermissionError(
                    f"Role '{role}' is not in required roles {roles} "
                    f"for {fn.__name__}"
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
