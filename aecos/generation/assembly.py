"""Assembly generation — groups of related elements.

An assembly is a parent folder containing sub-element folders and an
``assembly_manifest.json`` linking them with IFC relationship types.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from aecos.generation.generator import ElementGenerator
from aecos.nlp.schema import ParametricSpec

logger = logging.getLogger(__name__)


class AssemblyGenerator:
    """Generate assemblies of related elements.

    Parameters
    ----------
    output_dir:
        Directory in which assembly folders are created.
    compliance_engine:
        Optional ComplianceEngine passed to individual ElementGenerators.
    """

    def __init__(
        self,
        output_dir: str | Path,
        compliance_engine: Any | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.compliance_engine = compliance_engine

    def generate(
        self,
        specs: list[ParametricSpec],
        relationships: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Generate a multi-element assembly.

        Parameters
        ----------
        specs:
            List of ParametricSpecs, one per sub-element.
        relationships:
            Optional list of relationship dicts, each containing:
              - ``type``: IFC relationship type (e.g. 'IfcRelAggregates')
              - ``source_index``: index into specs for the source element
              - ``target_index``: index into specs for the target element

        Returns the path to the assembly folder.
        """
        relationships = relationships or []
        assembly_id = uuid.uuid4().hex[:16].upper()
        assembly_folder = self.output_dir / f"assembly_{assembly_id}"
        assembly_folder.mkdir(parents=True, exist_ok=True)

        # Generate each sub-element into the assembly folder
        gen = ElementGenerator(assembly_folder, compliance_engine=self.compliance_engine)
        element_folders: list[Path] = []
        element_ids: list[str] = []

        for spec in specs:
            folder = gen.generate(spec)
            element_folders.append(folder)
            # Read back the GlobalId from the generated metadata
            meta_path = folder / "metadata.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                element_ids.append(meta.get("GlobalId", folder.name))
            else:
                element_ids.append(folder.name)

        # Build manifest
        manifest: dict[str, Any] = {
            "assembly_id": assembly_id,
            "elements": [
                {
                    "index": i,
                    "global_id": eid,
                    "ifc_class": spec.ifc_class,
                    "name": spec.name or spec.ifc_class,
                    "folder": folder.name,
                }
                for i, (spec, eid, folder) in enumerate(
                    zip(specs, element_ids, element_folders)
                )
            ],
            "relationships": [
                {
                    "type": rel.get("type", "IfcRelAggregates"),
                    "source": element_ids[rel.get("source_index", 0)]
                    if rel.get("source_index", 0) < len(element_ids) else "",
                    "target": element_ids[rel.get("target_index", 0)]
                    if rel.get("target_index", 0) < len(element_ids) else "",
                }
                for rel in relationships
            ],
        }

        manifest_path = assembly_folder / "assembly_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8"
        )

        logger.info("Generated assembly %s with %d elements", assembly_id, len(specs))
        return assembly_folder
