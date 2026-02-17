"""ElementGenerator — main entry point for parametric generation.

Usage::

    from aecos.generation import ElementGenerator
    from aecos.nlp.schema import ParametricSpec

    gen = ElementGenerator(output_dir=Path("elements"))
    spec = ParametricSpec(ifc_class="IfcWall", properties={"thickness_mm": 200})
    folder = gen.generate(spec)
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from aecos.generation.builders import get_builder
from aecos.generation.folder_writer import write_element_folder
from aecos.metadata.generator import generate_metadata
from aecos.nlp.schema import ParametricSpec

logger = logging.getLogger(__name__)


class ElementGenerator:
    """Parametric element generator.

    Parameters
    ----------
    output_dir:
        Directory in which element folders are created.
    compliance_engine:
        Optional ComplianceEngine instance.  When provided, specs are
        checked (and optionally auto-adjusted) before generation.
    """

    def __init__(
        self,
        output_dir: str | Path,
        compliance_engine: Any | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.compliance_engine = compliance_engine

    def generate(self, spec: ParametricSpec) -> Path:
        """Generate an element folder from a ParametricSpec.

        1. Optionally runs ComplianceEngine.check() and adjusts spec.
        2. Selects appropriate builder by ifc_class.
        3. Builder produces JSON data.
        4. folder_writer creates the canonical folder structure.

        Returns the path to the completed element folder.
        """
        # Run compliance check if engine available
        if self.compliance_engine is not None:
            spec = self._apply_compliance(spec)

        builder = get_builder(spec.ifc_class)
        global_id = uuid.uuid4().hex[:22].upper()
        name = spec.name or f"{spec.ifc_class}_{global_id[:8]}"

        psets = builder.build_psets(spec.properties, spec.performance)
        materials = builder.build_materials(spec.materials, spec.properties)
        geometry = builder.build_geometry(spec.properties)
        spatial = builder.build_spatial()

        folder = write_element_folder(
            output_dir=self.output_dir,
            global_id=global_id,
            ifc_class=spec.ifc_class or builder.ifc_class,
            name=name,
            psets=psets,
            materials=materials,
            geometry=geometry,
            spatial=spatial,
        )

        logger.info("Generated element %s (%s) at %s", name, spec.ifc_class, folder)
        return folder

    def generate_from_template(
        self,
        template_folder: str | Path,
        overrides: dict[str, Any] | None = None,
    ) -> Path:
        """Generate an element by loading a template and applying overrides.

        Parameters
        ----------
        template_folder:
            Path to an existing template or element folder.
        overrides:
            Dict of property overrides to apply.  Keys follow the same
            convention as ParametricSpec.properties.

        Returns the path to the new element folder.
        """
        template_folder = Path(template_folder)
        overrides = overrides or {}

        # Load template metadata
        meta_path = template_folder / "metadata.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Template metadata not found: {meta_path}")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ifc_class = meta.get("IFCClass", "IfcWall")

        # Load existing psets
        psets_path = template_folder / "properties" / "psets.json"
        psets: dict[str, dict[str, Any]] = {}
        if psets_path.is_file():
            psets = json.loads(psets_path.read_text(encoding="utf-8"))

        # Load existing materials
        mat_path = template_folder / "materials" / "materials.json"
        materials: list[dict[str, Any]] = []
        if mat_path.is_file():
            raw = json.loads(mat_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                materials = raw

        # Apply property overrides into the Dimensions pset
        if overrides:
            if "Dimensions" not in psets:
                psets["Dimensions"] = {}
            psets["Dimensions"].update(overrides)

        # Rebuild geometry with merged properties
        merged_props = {}
        for pset_props in psets.values():
            merged_props.update(pset_props)

        builder = get_builder(ifc_class)
        geometry = builder.build_geometry(merged_props)
        spatial = builder.build_spatial()

        global_id = uuid.uuid4().hex[:22].upper()
        name = meta.get("Name", ifc_class) + "_modified"

        folder = write_element_folder(
            output_dir=self.output_dir,
            global_id=global_id,
            ifc_class=ifc_class,
            name=name,
            psets=psets,
            materials=materials,
            geometry=geometry,
            spatial=spatial,
        )

        logger.info("Generated from template %s -> %s", template_folder.name, folder)
        return folder

    def _apply_compliance(self, spec: ParametricSpec) -> ParametricSpec:
        """Check spec against compliance engine and adjust if non-compliant."""
        try:
            report = self.compliance_engine.check(spec)
            if report.status == "non_compliant":
                # Apply suggested fixes where possible
                spec = self._auto_adjust(spec, report)
                logger.info("Auto-adjusted spec for compliance")
        except Exception:
            logger.debug("Compliance check failed, proceeding with original spec", exc_info=True)
        return spec

    @staticmethod
    def _auto_adjust(spec: ParametricSpec, report: Any) -> ParametricSpec:
        """Apply automatic adjustments from compliance failures.

        This creates a new ParametricSpec with adjusted properties based
        on the compliance report's suggested fixes and rule results.
        """
        props = dict(spec.properties)
        perf = dict(spec.performance)

        for result in getattr(report, "results", []):
            if result.status != "fail":
                continue
            # Auto-adjust min_value failures
            if hasattr(result, "expected_value") and result.expected_value is not None:
                path = getattr(result, "title", "").lower()
                if "thickness" in path and isinstance(result.expected_value, (int, float)):
                    if props.get("thickness_mm", 0) < result.expected_value:
                        props["thickness_mm"] = result.expected_value
                if "fire" in path and "rating" in path:
                    perf["fire_rating"] = str(result.expected_value)

        return spec.model_copy(update={"properties": props, "performance": perf})
