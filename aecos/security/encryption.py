"""EncryptionManager — file-level encryption with provider fallback.

Uses Fernet (from cryptography) when available, falls back to a minimal
XOR provider for testing/demo.  The XOR provider is NOT secure.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class EncryptionProvider(ABC):
    """Abstract encryption provider."""

    @abstractmethod
    def encrypt(self, data: bytes, key: bytes) -> bytes: ...

    @abstractmethod
    def decrypt(self, data: bytes, key: bytes) -> bytes: ...

    @abstractmethod
    def generate_key(self) -> bytes: ...


# ---------------------------------------------------------------------------
# XOR fallback (NOT SECURE — demo / testing only)
# ---------------------------------------------------------------------------

class XORProvider(EncryptionProvider):
    """Minimal XOR cipher.  **Not secure** — for testing/demo only."""

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

    def decrypt(self, data: bytes, key: bytes) -> bytes:
        return self.encrypt(data, key)  # XOR is symmetric

    def generate_key(self) -> bytes:
        return os.urandom(32)


# ---------------------------------------------------------------------------
# Fernet provider (optional — requires cryptography)
# ---------------------------------------------------------------------------

class FernetProvider(EncryptionProvider):
    """Fernet symmetric encryption via the *cryptography* package."""

    def __init__(self) -> None:
        from cryptography.fernet import Fernet  # noqa: F401
        self._fernet_cls = Fernet

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        f = self._fernet_cls(key)
        return f.encrypt(data)

    def decrypt(self, data: bytes, key: bytes) -> bytes:
        f = self._fernet_cls(key)
        return f.decrypt(data)

    def generate_key(self) -> bytes:
        return self._fernet_cls.generate_key()


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

def _detect_provider() -> EncryptionProvider:
    """Return FernetProvider if available, otherwise XORProvider."""
    try:
        return FernetProvider()
    except BaseException:
        logger.info("cryptography not available — using XOR fallback (NOT SECURE)")
        return XORProvider()


class EncryptionManager:
    """File-level encryption / decryption.

    Parameters
    ----------
    project_root:
        AEC OS project root (for keystore location).
    provider:
        Explicit provider override (auto-detected if *None*).
    """

    def __init__(
        self,
        project_root: str | Path | None = None,
        provider: EncryptionProvider | None = None,
    ) -> None:
        self.provider = provider or _detect_provider()
        self._project_root = Path(project_root) if project_root else None
        self._keystore_path = (
            self._project_root / ".aecos" / "keystore.json"
            if self._project_root
            else None
        )

    # -- Key management -----------------------------------------------------

    def generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return self.provider.generate_key()

    def store_key(self, name: str, key: bytes) -> None:
        """Store a named key in the project keystore."""
        if not self._keystore_path:
            raise RuntimeError("No project root — cannot store key")
        self._keystore_path.parent.mkdir(parents=True, exist_ok=True)
        store = self._load_keystore()
        store[name] = base64.b64encode(key).decode()
        self._keystore_path.write_text(json.dumps(store, indent=2), encoding="utf-8")

    def load_key(self, name: str) -> bytes:
        """Load a named key from the project keystore."""
        store = self._load_keystore()
        encoded = store.get(name)
        if not encoded:
            raise KeyError(f"Key '{name}' not found in keystore")
        return base64.b64decode(encoded)

    # -- File encryption ----------------------------------------------------

    def encrypt_file(self, path: str | Path, key: bytes) -> Path:
        """Encrypt a file in-place. Returns the file path."""
        p = Path(path)
        data = p.read_bytes()
        encrypted = self.provider.encrypt(data, key)
        p.write_bytes(encrypted)
        return p

    def decrypt_file(self, path: str | Path, key: bytes) -> Path:
        """Decrypt a file in-place. Returns the file path."""
        p = Path(path)
        data = p.read_bytes()
        decrypted = self.provider.decrypt(data, key)
        p.write_bytes(decrypted)
        return p

    def encrypt_folder(
        self,
        path: str | Path,
        key: bytes,
        patterns: list[str] | None = None,
    ) -> list[Path]:
        """Encrypt matching files in a folder.

        Parameters
        ----------
        patterns:
            File extension patterns to match (e.g. ``['.json', '.ifc']``).
            If *None*, encrypts all files.
        """
        p = Path(path)
        encrypted: list[Path] = []
        for f in p.rglob("*"):
            if not f.is_file():
                continue
            if patterns and f.suffix not in patterns:
                continue
            self.encrypt_file(f, key)
            encrypted.append(f)
        return encrypted

    # -- Internals ----------------------------------------------------------

    def _load_keystore(self) -> dict[str, Any]:
        if self._keystore_path and self._keystore_path.is_file():
            try:
                return json.loads(self._keystore_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}
