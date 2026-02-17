"""AecOS — the single unified entry point for all AEC OS operations.

Usage::

    from aecos import AecOS

    os = AecOS(project_root="/path/to/project")
    os.extract_ifc("building.ifc")
    os.search(ifc_class="IfcWall", material="concrete")
    os.promote_to_template(element_id, tags={...})
    os.commit("Added new wall elements")
    os.parse("2-hour fire-rated concrete wall, 12 feet tall")
    os.check_compliance(element_or_spec)
    os.generate("150mm concrete wall, 2hr fire rated, California")
    os.validate(element_folder)
    os.estimate_cost(element_folder)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aecos.api import elements as elem_ops
from aecos.api import projects as proj_ops
from aecos.api import search as search_ops
from aecos.api import templates as tmpl_ops
from aecos.api.search import SearchResults
from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.report import ComplianceReport
from aecos.cost.engine import CostEngine
from aecos.cost.report import CostReport
from aecos.generation.generator import ElementGenerator
from aecos.metadata.generator import generate_metadata
from aecos.models.element import Element
from aecos.nlp.parser import NLParser
from aecos.nlp.schema import ParametricSpec
from aecos.templates.library import TemplateLibrary
from aecos.templates.registry import RegistryEntry
from aecos.templates.tagging import TemplateTags
from aecos.validation.report import ValidationReport
from aecos.validation.validator import Validator
from aecos.vcs.commits import commit_all
from aecos.vcs.repo import RepoManager

logger = logging.getLogger(__name__)


class AecOS:
    """The public interface for the AEC OS.

    Auto-detects or initialises a git repo and template library at the
    given project root.  Every mutating operation auto-generates metadata
    (Item 03) and auto-commits (Item 04).

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    auto_commit:
        If *True* (default), every mutating operation creates a git
        commit automatically.
    """

    def __init__(
        self,
        project_root: str | Path,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.auto_commit = auto_commit

        # Auto-detect or initialise git repo
        self.repo = RepoManager(self.project_root)
        if not self.repo.is_repo():
            self.repo.init_repo()

        # Ensure project directories exist
        (self.project_root / "elements").mkdir(parents=True, exist_ok=True)

        # Initialise template library
        templates_dir = self.project_root / "templates"
        self.library = TemplateLibrary(templates_dir)

        # Initialise NL parser and compliance engine (Items 06, 07)
        self.parser = NLParser()
        self.compliance = ComplianceEngine()

        # Initialise generation, validation, and cost engines (Items 08, 09, 10)
        self.generator = ElementGenerator(
            self.project_root / "elements",
            compliance_engine=self.compliance,
        )
        self.validator = Validator()
        self.cost_engine = CostEngine()

    # -- Element CRUD ---------------------------------------------------------

    def create_element(
        self,
        ifc_class: str,
        *,
        name: str | None = None,
        properties: dict[str, dict[str, Any]] | None = None,
        materials: list[dict[str, Any]] | None = None,
    ) -> Element:
        """Create a new element folder from scratch.

        Returns the created :class:`Element`.
        """
        elem = elem_ops.create_element(
            self.project_root,
            ifc_class,
            name=name,
            properties=properties,
            materials=materials,
        )

        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"feat: create element {elem.name} ({ifc_class})",
                )
            except Exception:
                logger.debug("Auto-commit failed for create_element", exc_info=True)

        return elem

    def get_element(self, element_id: str) -> Element | None:
        """Load an element by its GlobalId."""
        return elem_ops.get_element(self.project_root, element_id)

    def update_element(self, element_id: str, updates: dict[str, Any]) -> Element:
        """Update an existing element's metadata/properties.

        Returns the updated :class:`Element`.
        """
        elem = elem_ops.update_element(self.project_root, element_id, updates)

        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"fix: update element {element_id}",
                )
            except Exception:
                logger.debug("Auto-commit failed for update_element", exc_info=True)

        return elem

    def delete_element(self, element_id: str) -> bool:
        """Remove an element folder.  Returns *True* if it existed."""
        deleted = elem_ops.delete_element(self.project_root, element_id)

        if deleted and self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"chore: delete element {element_id}",
                )
            except Exception:
                logger.debug("Auto-commit failed for delete_element", exc_info=True)

        return deleted

    def list_elements(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[Element]:
        """List all elements in the project, optionally filtered."""
        return elem_ops.list_elements(self.project_root, filters)

    # -- Template operations --------------------------------------------------

    def promote_to_template(
        self,
        element_id: str,
        *,
        tags: TemplateTags | dict[str, Any] | None = None,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
    ) -> Path:
        """Promote an extracted element to a library template.

        Returns the path to the new template folder.
        """
        element_folder = self.project_root / "elements" / f"element_{element_id}"
        return tmpl_ops.promote_to_template(
            self.library,
            element_folder,
            repo=self.repo if self.auto_commit else None,
            tags=tags,
            version=version,
            author=author,
            description=description,
            auto_commit=self.auto_commit,
        )

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
        """Add a template to the library."""
        return tmpl_ops.add_template(
            self.library,
            template_id,
            source_folder,
            repo=self.repo if self.auto_commit else None,
            tags=tags,
            version=version,
            author=author,
            description=description,
            auto_commit=self.auto_commit,
        )

    def remove_template(self, template_id: str) -> bool:
        """Remove a template from the library."""
        return tmpl_ops.remove_template(
            self.library,
            template_id,
            repo=self.repo if self.auto_commit else None,
            auto_commit=self.auto_commit,
        )

    def search_templates(self, query: dict[str, object]) -> list[RegistryEntry]:
        """Search the template library."""
        return tmpl_ops.search_templates(self.library, query)

    # -- Unified search -------------------------------------------------------

    def search(
        self,
        *,
        ifc_class: str | None = None,
        material: str | None = None,
        name: str | None = None,
        region: str | None = None,
        keyword: str | None = None,
    ) -> SearchResults:
        """Search across both project elements and the template library."""
        return search_ops.unified_search(
            self.project_root,
            self.library,
            ifc_class=ifc_class,
            material=material,
            name=name,
            region=region,
            keyword=keyword,
        )

    # -- Project operations ---------------------------------------------------

    @staticmethod
    def init_project(path: str | Path, name: str = "AEC OS Project") -> Path:
        """Create a new AEC OS project with git, templates, and config.

        Returns the project root path.
        """
        return proj_ops.init_project(path, name)

    def extract_ifc(self, ifc_path: str | Path) -> list[Element]:
        """Run the full extraction pipeline on an IFC file.

        Orchestrates: extraction -> metadata -> auto-commit.

        Returns the list of extracted :class:`Element` models.
        """
        return proj_ops.extract_ifc(
            self.project_root,
            ifc_path,
            repo=self.repo if self.auto_commit else None,
            auto_commit=self.auto_commit,
        )

    def bulk_promote(
        self,
        element_ids: list[str],
        *,
        tags: TemplateTags | dict[str, Any] | None = None,
    ) -> list[Path]:
        """Promote multiple elements to templates in one operation."""
        return proj_ops.bulk_promote(
            self.project_root,
            self.library,
            element_ids,
            tags=tags,
            repo=self.repo if self.auto_commit else None,
            auto_commit=self.auto_commit,
        )

    # -- Natural language parsing (Item 06) -----------------------------------

    def parse(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> ParametricSpec:
        """Parse a plain-English building description into a ParametricSpec.

        Parameters
        ----------
        text:
            Natural-language building specification.
        context:
            Optional dict with ``project_type``, ``climate_zone``,
            ``jurisdiction``, etc.
        """
        return self.parser.parse(text, context)

    # -- Compliance checking (Item 07) ----------------------------------------

    def check_compliance(
        self,
        element_or_spec: Any,
        *,
        region: str | None = None,
    ) -> ComplianceReport:
        """Check an element or spec against the compliance rule database.

        Parameters
        ----------
        element_or_spec:
            An ``Element`` or ``ParametricSpec``.
        region:
            Override region for rule filtering.
        """
        return self.compliance.check(element_or_spec, region=region)

    # -- Parametric generation (Item 08) --------------------------------------

    def generate(
        self,
        text_or_spec: str | ParametricSpec,
        context: dict[str, Any] | None = None,
    ) -> Path:
        """Full pipeline: parse -> comply -> generate -> validate -> cost -> metadata -> commit.

        Parameters
        ----------
        text_or_spec:
            Natural-language text or a ParametricSpec.
        context:
            Optional parsing context.

        Returns the path to the generated element folder.
        """
        # 1. Parse
        if isinstance(text_or_spec, str):
            spec = self.parser.parse(text_or_spec, context)
        else:
            spec = text_or_spec

        # 2. Compliance
        compliance_report = self.compliance.check(spec)

        # 3. Generate
        element_folder = self.generator.generate(spec)

        # 4. Validate
        validation_report = self.validator.validate(element_folder)

        # 5. Cost
        cost_report = self.cost_engine.estimate(element_folder)

        # 6. Regenerate metadata with real report data
        try:
            generate_metadata(
                element_folder,
                compliance_report=compliance_report,
                cost_report=cost_report,
                validation_report=validation_report,
            )
        except Exception:
            logger.debug("Metadata regeneration failed", exc_info=True)

        # 7. Auto-commit
        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"feat: generate element {spec.ifc_class} ({element_folder.name})",
                )
            except Exception:
                logger.debug("Auto-commit failed for generate", exc_info=True)

        return element_folder

    def generate_from_template(
        self,
        template_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> Path:
        """Generate an element from a template with overrides.

        Same pipeline as :meth:`generate` but starts from a template base.
        """
        template_folder = self.library.get_template(template_id)
        if template_folder is None:
            raise FileNotFoundError(f"Template not found: {template_id}")

        element_folder = self.generator.generate_from_template(template_folder, overrides)

        # Run validation and cost
        validation_report = self.validator.validate(element_folder)
        cost_report = self.cost_engine.estimate(element_folder)

        try:
            generate_metadata(
                element_folder,
                cost_report=cost_report,
                validation_report=validation_report,
            )
        except Exception:
            logger.debug("Metadata regeneration failed", exc_info=True)

        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"feat: generate from template {template_id} ({element_folder.name})",
                )
            except Exception:
                logger.debug("Auto-commit failed for generate_from_template", exc_info=True)

        return element_folder

    # -- Validation (Item 09) -------------------------------------------------

    def validate(
        self,
        element_folder: str | Path,
        context: list[str | Path] | None = None,
    ) -> ValidationReport:
        """Validate an element folder.

        Parameters
        ----------
        element_folder:
            Path to the element folder.
        context:
            Optional list of context element folder paths for clash detection.
        """
        return self.validator.validate(element_folder, context_elements=context)

    # -- Cost estimation (Item 10) --------------------------------------------

    def estimate_cost(
        self,
        element_folder_or_spec: Any,
        *,
        region: str | None = None,
    ) -> CostReport:
        """Estimate cost and schedule for an element.

        Parameters
        ----------
        element_folder_or_spec:
            Path to element folder, or a ParametricSpec.
        region:
            Override region code.
        """
        return self.cost_engine.estimate(element_folder_or_spec, region=region)

    # -- Direct VCS access ----------------------------------------------------

    def commit(self, message: str) -> str:
        """Create a manual commit of all pending changes.

        Returns the short commit hash, or empty string if clean.
        """
        return commit_all(self.repo, message)

    def status(self) -> str:
        """Return the git status (porcelain format)."""
        return self.repo.status()

    def is_clean(self) -> bool:
        """Return *True* if the working tree has no uncommitted changes."""
        return self.repo.is_clean()
