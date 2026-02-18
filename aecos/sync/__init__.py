"""Multi-User Sync — team collaboration for AEC OS."""

from aecos.sync.conflict import ConflictResult, merge_json, merge_markdown
from aecos.sync.locking import LockInfo, LockManager
from aecos.sync.manager import SyncManager
from aecos.sync.notifications import ConsoleNotifier, NotificationProvider
from aecos.sync.permissions import PermissionManager, Role

__all__ = [
    "ConflictResult",
    "ConsoleNotifier",
    "LockInfo",
    "LockManager",
    "NotificationProvider",
    "PermissionManager",
    "Role",
    "SyncManager",
    "merge_json",
    "merge_markdown",
]
