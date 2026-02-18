"""Soft file locking for concurrent editing protection."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LOCK_TIMEOUT = 3600  # 1 hour in seconds


@dataclass
class LockInfo:
    """Information about an active lock."""

    element_id: str
    user_id: str
    timestamp: float
    timeout: float = DEFAULT_LOCK_TIMEOUT

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.timeout

    def to_dict(self) -> dict:
        return {
            "element_id": self.element_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LockInfo:
        return cls(
            element_id=data["element_id"],
            user_id=data["user_id"],
            timestamp=data.get("timestamp", 0),
            timeout=data.get("timeout", DEFAULT_LOCK_TIMEOUT),
        )


class LockManager:
    """Manage advisory locks on element folders.

    Locks are stored as ``.lock`` files inside element folders.
    They are advisory only (not enforced at git level) and expire
    after the configured timeout (default 1 hour).

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    timeout:
        Lock timeout in seconds.
    """

    def __init__(
        self,
        project_root: str | Path,
        timeout: float = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        self.project_root = Path(project_root)
        self.timeout = timeout

    def lock_element(
        self,
        element_id: str,
        user_id: str,
    ) -> LockInfo:
        """Create a lock on an element.

        Parameters
        ----------
        element_id:
            Element GlobalId.
        user_id:
            User who is locking the element.

        Returns
        -------
        LockInfo
            The created lock.

        Raises
        ------
        RuntimeError
            If the element is already locked by another user.
        """
        existing = self.is_locked(element_id)
        if existing and existing.user_id != user_id:
            raise RuntimeError(
                f"Element '{element_id}' is locked by '{existing.user_id}'."
            )

        lock = LockInfo(
            element_id=element_id,
            user_id=user_id,
            timestamp=time.time(),
            timeout=self.timeout,
        )

        lock_path = self._lock_path(element_id)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(
            json.dumps(lock.to_dict(), indent=2), encoding="utf-8",
        )

        logger.info("Locked element %s for user %s", element_id, user_id)
        return lock

    def unlock_element(self, element_id: str, user_id: str) -> bool:
        """Remove a lock on an element.

        Only the lock holder or an admin can unlock.

        Returns True if the lock was removed.
        """
        lock_path = self._lock_path(element_id)
        if not lock_path.is_file():
            return False

        existing = self.is_locked(element_id)
        if existing and existing.user_id != user_id:
            raise RuntimeError(
                f"Cannot unlock: element '{element_id}' is locked by "
                f"'{existing.user_id}', not '{user_id}'."
            )

        lock_path.unlink()
        logger.info("Unlocked element %s by user %s", element_id, user_id)
        return True

    def is_locked(self, element_id: str) -> LockInfo | None:
        """Check if an element is locked.

        Returns the LockInfo if locked (and not expired), or None.
        Stale locks are auto-expired and cleaned up.
        """
        lock_path = self._lock_path(element_id)
        if not lock_path.is_file():
            return None

        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            lock = LockInfo.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            # Corrupted lock file — clean up
            lock_path.unlink(missing_ok=True)
            return None

        if lock.is_expired:
            # Auto-expire stale lock
            logger.info(
                "Auto-expiring stale lock on %s (held by %s)",
                element_id, lock.user_id,
            )
            lock_path.unlink(missing_ok=True)
            return None

        return lock

    def force_unlock(self, element_id: str) -> bool:
        """Force-remove a lock regardless of holder. Admin use only."""
        lock_path = self._lock_path(element_id)
        if lock_path.is_file():
            lock_path.unlink()
            logger.info("Force-unlocked element %s", element_id)
            return True
        return False

    def _lock_path(self, element_id: str) -> Path:
        """Compute the lock file path for an element."""
        return self.project_root / "elements" / f"element_{element_id}" / ".lock"
