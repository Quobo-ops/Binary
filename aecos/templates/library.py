"""TemplateLibrary — CRUD manager for the local template directory.

A *template* is an Element folder (same structure produced by Item 01's
extraction pipeline) plus a ``template_manifest.json`` file that carries
tags, version, author, region, and compliance codes.

The library root contains:
  * ``registry.json`` — fast index of all templates
  * One sub-directory per template, named ``template_<id>/``

Every mutating method (add / update / remove / promote) persists the
registry atomically so the on-disk state is always consistent.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from aecos.metadata.generator import generate_metadata
from aecos.templates.registry import RegistryEntry, TemplateRegistry
from aecos.templates.search import search as _search
from aecos.templates.tagging import TemplateTags

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "template_manifest.json"


def _read_manifest(folder: Path) -> dict[str, Any]:
    """Read and return the template manifest from *folder*."""
    manifest_path = folder / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _write_manifest(folder: Path, manifest: dict[str, Any]) -> None:
    """Write *manifest* as ``template_manifest.json`` inside *folder*."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


class TemplateLibrary:
    """Manage a local directory of template folders.

    Parameters
    ----------
    root:
        Path to the library directory.  Created on first write if it
        does not exist.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry = TemplateRegistry(self.root)

    # -- helpers --------------------------------------------------------------

    def _template_dir(self, template_id: str) -> Path:
        return self.root / f"template_{template_id}"

    # -- CRUD -----------------------------------------------------------------

    def add_template(
        self,
        template_id: str,
        source_folder: str | Path,
        *,
        tags: TemplateTags | dict[str, Any] | None = None,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
    ) -> Path:
        """Copy *source_folder* into the library and register it.

        Parameters
        ----------
        template_id:
            Unique identifier for the template (typically the element
            ``global_id``).
        source_folder:
            An existing Element folder to import.
        tags:
            Tag data — a :class:`TemplateTags` instance or raw dict.
        version, author, description:
            Optional metadata written to the manifest.

        Returns
        -------
        Path
            The newly created template folder inside the library.
        """
        source_folder = Path(source_folder)
        if not source_folder.is_dir():
            raise FileNotFoundError(f"Source folder not found: {source_folder}")

        if isinstance(tags, dict):
            tags = TemplateTags.model_validate(tags)
        elif tags is None:
            tags = TemplateTags()

        dest = self._template_dir(template_id)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_folder, dest)

        # Write manifest
        manifest: dict[str, Any] = {
            "template_id": template_id,
            "tags": tags.model_dump(mode="json"),
            "version": version,
            "author": author,
            "description": description,
        }
        _write_manifest(dest, manifest)

        # Update registry
        entry = RegistryEntry(
            template_id=template_id,
            folder_name=dest.name,
            tags=tags,
            version=version,
            author=author,
            description=description,
        )
        self.registry.add(entry)
        self.registry.save()

        # Regenerate Markdown with template-specific info (Item 03 integration)
        try:
            generate_metadata(dest)
        except Exception:
            logger.debug(
                "Metadata generation failed for template %s",
                template_id,
                exc_info=True,
            )

        logger.info("Added template %s -> %s", template_id, dest)
        return dest

    def get_template(self, template_id: str) -> Path | None:
        """Return the template folder path, or *None* if not found."""
        entry = self.registry.get(template_id)
        if entry is None:
            return None
        folder = self.root / entry.folder_name
        if not folder.is_dir():
            return None
        return folder

    def get_manifest(self, template_id: str) -> dict[str, Any] | None:
        """Return the parsed manifest dict for *template_id*."""
        folder = self.get_template(template_id)
        if folder is None:
            return None
        return _read_manifest(folder)

    def update_template(
        self,
        template_id: str,
        *,
        tags: TemplateTags | dict[str, Any] | None = None,
        version: str | None = None,
        author: str | None = None,
        description: str | None = None,
    ) -> Path:
        """Update metadata for an existing template.

        Only the provided keyword arguments are changed; everything else
        is preserved.

        Returns
        -------
        Path
            The template folder.

        Raises
        ------
        KeyError
            If *template_id* is not in the registry.
        """
        entry = self.registry.get(template_id)
        if entry is None:
            raise KeyError(f"Template not found: {template_id}")

        folder = self.root / entry.folder_name

        if isinstance(tags, dict):
            entry.tags = TemplateTags.model_validate(tags)
        elif isinstance(tags, TemplateTags):
            entry.tags = tags

        if version is not None:
            entry.version = version
        if author is not None:
            entry.author = author
        if description is not None:
            entry.description = description

        # Re-write manifest
        manifest = {
            "template_id": entry.template_id,
            "tags": entry.tags.model_dump(mode="json"),
            "version": entry.version,
            "author": entry.author,
            "description": entry.description,
        }
        _write_manifest(folder, manifest)

        self.registry.add(entry)
        self.registry.save()

        logger.info("Updated template %s", template_id)
        return folder

    def remove_template(self, template_id: str) -> bool:
        """Remove a template from the library and registry.

        Returns *True* if the template existed, *False* otherwise.
        """
        entry = self.registry.remove(template_id)
        if entry is None:
            return False

        folder = self.root / entry.folder_name
        if folder.is_dir():
            shutil.rmtree(folder)

        self.registry.save()
        logger.info("Removed template %s", template_id)
        return True

    # -- Search ---------------------------------------------------------------

    def search(self, query: dict[str, object]) -> list[RegistryEntry]:
        """Search templates by tag, type, keyword, or description.

        See :func:`aecos.templates.search.search` for supported query
        keys.
        """
        return _search(self.registry, query)

    # -- Promote --------------------------------------------------------------

    def promote_to_template(
        self,
        element_folder: str | Path,
        *,
        tags: TemplateTags | dict[str, Any] | None = None,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        template_id: str | None = None,
    ) -> Path:
        """Promote an extracted Element folder to a library template.

        The element's ``metadata.json`` is read to derive the template
        id (from GlobalId) if *template_id* is not supplied.  The folder
        is copied into the library, a ``template_manifest.json`` is
        written, and the registry is updated.

        Returns the path to the new template folder.
        """
        element_folder = Path(element_folder)
        if not element_folder.is_dir():
            raise FileNotFoundError(f"Element folder not found: {element_folder}")

        # Derive template_id from metadata.json if not provided
        if template_id is None:
            meta_path = element_folder / "metadata.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                template_id = meta.get("GlobalId", element_folder.name)
            else:
                template_id = element_folder.name

        # Auto-populate ifc_class tag from metadata if not set
        if tags is None:
            tags = TemplateTags()
        if isinstance(tags, dict):
            tags = TemplateTags.model_validate(tags)

        if tags.ifc_class is None:
            meta_path = element_folder / "metadata.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                tags.ifc_class = meta.get("IFCClass")

        return self.add_template(
            template_id,
            element_folder,
            tags=tags,
            version=version,
            author=author,
            description=description,
        )
