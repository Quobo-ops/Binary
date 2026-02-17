"""Template registry — a JSON manifest that indexes all templates for fast search.

The registry lives at ``<library_root>/registry.json`` and is the single
source of truth for which templates exist and what their tags are.  Every
mutating operation in :mod:`aecos.templates.library` updates the registry
atomically (write-to-temp then rename).
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from aecos.templates.tagging import TemplateTags

logger = logging.getLogger(__name__)

REGISTRY_FILENAME = "registry.json"


class RegistryEntry:
    """In-memory representation of one row in the registry."""

    __slots__ = ("template_id", "folder_name", "tags", "version", "author", "description")

    def __init__(
        self,
        template_id: str,
        folder_name: str,
        tags: TemplateTags,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
    ) -> None:
        self.template_id = template_id
        self.folder_name = folder_name
        self.tags = tags
        self.version = version
        self.author = author
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "folder_name": self.folder_name,
            "tags": self.tags.model_dump(mode="json"),
            "version": self.version,
            "author": self.author,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryEntry:
        return cls(
            template_id=data["template_id"],
            folder_name=data["folder_name"],
            tags=TemplateTags.model_validate(data.get("tags", {})),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
        )


class TemplateRegistry:
    """Read/write access to ``registry.json``."""

    def __init__(self, library_root: Path) -> None:
        self._root = library_root
        self._path = library_root / REGISTRY_FILENAME
        self._entries: dict[str, RegistryEntry] = {}
        self._load()

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if not self._path.is_file():
            self._entries = {}
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = {
                e["template_id"]: RegistryEntry.from_dict(e)
                for e in data.get("templates", [])
            }
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt registry at %s — starting fresh", self._path)
            self._entries = {}

    def save(self) -> None:
        """Atomically persist the registry to disk."""
        payload = {
            "version": "1",
            "templates": [e.to_dict() for e in self._entries.values()],
        }
        self._root.mkdir(parents=True, exist_ok=True)
        # Atomic write: temp file + rename
        fd, tmp = tempfile.mkstemp(
            dir=self._root, prefix=".registry_", suffix=".json"
        )
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            Path(tmp).replace(self._path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- CRUD helpers ---------------------------------------------------------

    def add(self, entry: RegistryEntry) -> None:
        self._entries[entry.template_id] = entry

    def get(self, template_id: str) -> RegistryEntry | None:
        return self._entries.get(template_id)

    def remove(self, template_id: str) -> RegistryEntry | None:
        return self._entries.pop(template_id, None)

    def list_all(self) -> list[RegistryEntry]:
        return list(self._entries.values())

    def __contains__(self, template_id: str) -> bool:
        return template_id in self._entries

    def __len__(self) -> int:
        return len(self._entries)
