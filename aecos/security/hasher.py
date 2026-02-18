"""Content hashing utilities using stdlib hashlib (SHA-256)."""

from __future__ import annotations

import hashlib
from pathlib import Path


class Hasher:
    """SHA-256 hashing for files, folders, and strings."""

    @staticmethod
    def hash_string(text: str) -> str:
        """Return the SHA-256 hex digest of *text*."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_file(path: str | Path) -> str:
        """Return the SHA-256 hex digest of the file at *path*."""
        h = hashlib.sha256()
        p = Path(path)
        with p.open("rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def hash_folder(path: str | Path) -> str:
        """Return a SHA-256 digest covering every file in *path*.

        Files are sorted by relative path so the hash is deterministic.
        """
        p = Path(path)
        h = hashlib.sha256()
        files = sorted(f for f in p.rglob("*") if f.is_file())
        for f in files:
            file_hash = Hasher.hash_file(f)
            rel = f.relative_to(p).as_posix()
            h.update(f"{rel}:{file_hash}".encode("utf-8"))
        return h.hexdigest()
