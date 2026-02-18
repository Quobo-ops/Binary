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
    os.export_visualization(element_folder, format="json3d")
    os.sync()
    os.evaluate_parser()
    os.list_domains()
    os.submit_regulatory_update("IBC2024", new_rules)
    os.add_comment(element_id, user, text)
    os.execute_command("add a concrete wall", user="alice")
    os.get_audit_log()
    os.verify_audit_chain()
    os.scan_security(project_path)
    os.get_kpis()
    os.generate_dashboard()
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from aecos.analytics.collector import MetricsCollector
from aecos.analytics.dashboard import DashboardGenerator
from aecos.analytics.exporter import ReportExporter
from aecos.analytics.kpi import KPICalculator
from aecos.analytics.warehouse import DataWarehouse
from aecos.api import elements as elem_ops
from aecos.api import projects as proj_ops
from aecos.api import search as search_ops
from aecos.api import templates as tmpl_ops
from aecos.api.search import SearchResults
from aecos.collaboration.manager import CollaborationManager
from aecos.collaboration.models import ActivityEvent, Comment, Review, Task
from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.report import ComplianceReport
from aecos.compliance.rules import Rule
from aecos.cost.engine import CostEngine
from aecos.cost.report import CostReport
from aecos.deployment.ci import CIGenerator
from aecos.deployment.config_manager import ConfigManager
from aecos.deployment.docker import DockerBuilder
from aecos.deployment.health import HealthChecker, HealthReport
from aecos.deployment.installer import Installer
from aecos.deployment.packager import SystemPackager
from aecos.deployment.rollback import RollbackManager
from aecos.domains.base import DomainPlugin
from aecos.domains.registry import DomainRegistry
from aecos.finetune.collector import InteractionCollector
from aecos.finetune.dataset import DatasetBuilder
from aecos.finetune.evaluator import EvaluationReport, ModelEvaluator
from aecos.finetune.feedback import FeedbackManager
from aecos.generation.generator import ElementGenerator
from aecos.metadata.generator import generate_metadata
from aecos.models.element import Element
from aecos.nlp.parser import NLParser
from aecos.nlp.schema import ParametricSpec
from aecos.regulatory.differ import RuleDiffer
from aecos.regulatory.impact import ImpactAnalyzer
from aecos.regulatory.monitor import UpdateCheckResult, UpdateMonitor
from aecos.regulatory.report import UpdateReport
from aecos.regulatory.updater import RuleUpdater
from aecos.security.audit import AuditEntry, AuditLogger
from aecos.security.encryption import EncryptionManager
from aecos.security.hasher import Hasher
from aecos.security.report import SecurityReport
from aecos.security.scanner import SecurityScanner
from aecos.sync.locking import LockInfo
from aecos.sync.manager import SyncManager
from aecos.templates.library import TemplateLibrary
from aecos.templates.registry import RegistryEntry
from aecos.templates.tagging import TemplateTags
from aecos.validation.report import ValidationReport
from aecos.validation.validator import Validator
from aecos.vcs.commits import commit_all
from aecos.vcs.repo import RepoManager
from aecos.visualization.bridge import ExportResult, VisualizationBridge

logger = logging.getLogger(__name__)


def _safe_dump(obj: Any) -> str:
    """Serialize an object to string for hashing, regardless of type."""
    if hasattr(obj, "model_dump"):
        return str(obj.model_dump())
    if hasattr(obj, "to_dict"):
        return str(obj.to_dict())
    return str(obj)


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

        # Initialise fine-tuning collector (Item 13)
        self._collector = InteractionCollector(
            self.project_root / "fine_tuning" / "interactions",
        )

        # Initialise NL parser with collector (Items 06, 13)
        self.parser = NLParser(collector=self._collector)
        self.compliance = ComplianceEngine()

        # Initialise generation, validation, and cost engines (Items 08, 09, 10)
        self.generator = ElementGenerator(
            self.project_root / "elements",
            compliance_engine=self.compliance,
        )
        self.validator = Validator()
        self.cost_engine = CostEngine()

        # Initialise visualization bridge (Item 11)
        self.viz = VisualizationBridge()

        # Fine-tuning subsystems (Item 13)
        self._feedback = FeedbackManager(self._collector)
        self._dataset_builder = DatasetBuilder(
            self._collector,
            self.project_root / "fine_tuning" / "datasets",
        )
        self._evaluator = ModelEvaluator()

        # Domain expansion (Item 14) — auto-discover and inject
        self.domain_registry = DomainRegistry()
        self.domain_registry.auto_discover()
        self.domain_registry.apply_all(
            compliance_engine=self.compliance,
            parser=self.parser,
            cost_engine=self.cost_engine,
            validator=self.validator,
        )

        # Regulatory auto-update (Item 15)
        self._update_monitor = UpdateMonitor()
        self._rule_differ = RuleDiffer()
        self._rule_updater = RuleUpdater(self.compliance, self.project_root)
        self._impact_analyzer = ImpactAnalyzer(self.project_root)

        # Collaboration layer (Item 16)
        self.collaboration = CollaborationManager(
            self.project_root,
            aecos_facade=self,
        )

        # Security & Audit (Item 17)
        self.audit_logger = AuditLogger(":memory:")
        self.hasher = Hasher()
        self.encryption = EncryptionManager(self.project_root)
        self.security_scanner = SecurityScanner(audit_logger=self.audit_logger)

        # Analytics (Item 19)
        self.metrics = MetricsCollector(":memory:")
        self._warehouse = DataWarehouse(self.metrics._conn)
        self._kpi = KPICalculator(self._warehouse)
        self._dashboard_gen = DashboardGenerator(self._kpi, self._warehouse)
        self._report_exporter = ReportExporter()

        # Deployment (Item 18)
        self._packager = SystemPackager()
        self._installer = Installer()
        self._health_checker = HealthChecker()
        self._config_manager = ConfigManager()
        self._docker_builder = DockerBuilder()
        self._ci_generator = CIGenerator()
        self._rollback_manager = RollbackManager(self.project_root)

    # -- Internal audit/metrics helpers ---------------------------------------

    def _audit(
        self,
        user: str,
        action: str,
        resource: str = "",
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> None:
        """Log an audit event (best-effort)."""
        try:
            self.audit_logger.log(user, action, resource, before_hash, after_hash)
        except Exception:
            logger.debug("Audit logging failed", exc_info=True)

    def _record_metric(
        self,
        module: str,
        event_type: str,
        value: float | None = None,
        metadata: dict[str, Any] | None = None,
        user: str = "",
    ) -> None:
        """Record a metrics event (best-effort)."""
        try:
            self.metrics.record(module, event_type, value, metadata, user)
        except Exception:
            logger.debug("Metrics recording failed", exc_info=True)

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

        before = ""
        if element_folder.is_dir():
            before = self.hasher.hash_folder(element_folder)

        result = tmpl_ops.promote_to_template(
            self.library,
            element_folder,
            repo=self.repo if self.auto_commit else None,
            tags=tags,
            version=version,
            author=author,
            description=description,
            auto_commit=self.auto_commit,
        )

        after = self.hasher.hash_folder(result) if result.is_dir() else ""
        self._audit("system", "template_add", str(result), before, after)
        self._record_metric("template", "reuse_count", 1.0, {"template_id": element_id})

        return result

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
        result = tmpl_ops.add_template(
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

        after = self.hasher.hash_folder(result) if result.is_dir() else ""
        self._audit("system", "template_add", template_id, "", after)

        return result

    def remove_template(self, template_id: str) -> bool:
        """Remove a template from the library."""
        result = tmpl_ops.remove_template(
            self.library,
            template_id,
            repo=self.repo if self.auto_commit else None,
            auto_commit=self.auto_commit,
        )
        self._audit("system", "template_remove", template_id)
        return result

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
        result = proj_ops.extract_ifc(
            self.project_root,
            ifc_path,
            repo=self.repo if self.auto_commit else None,
            auto_commit=self.auto_commit,
        )
        self._record_metric(
            "extraction", "elements_extracted",
            float(len(result)),
            {"ifc_path": str(ifc_path)},
        )
        return result

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
        """Parse a plain-English building description into a ParametricSpec."""
        prompt_hash = self.hasher.hash_string(text)
        spec = self.parser.parse(text, context)
        result_hash = self.hasher.hash_string(_safe_dump(spec))

        self._audit("system", "parse", text[:100], prompt_hash, result_hash)

        confidence = getattr(spec, "confidence", 0.9)
        self._record_metric("parser", "parse_completed", confidence)

        return spec

    # -- Compliance checking (Item 07) ----------------------------------------

    def check_compliance(
        self,
        element_or_spec: Any,
        *,
        region: str | None = None,
    ) -> ComplianceReport:
        """Check an element or spec against the compliance rule database."""
        element_hash = self.hasher.hash_string(str(element_or_spec))
        report = self.compliance.check(element_or_spec, region=region)
        report_hash = self.hasher.hash_string(_safe_dump(report))

        self._audit("system", "compliance_check", "", element_hash, report_hash)

        passed = 1.0 if report.status == "compliant" else 0.0
        self._record_metric("compliance", "check_completed", passed)

        return report

    # -- Parametric generation (Item 08) --------------------------------------

    def generate(
        self,
        text_or_spec: str | ParametricSpec,
        context: dict[str, Any] | None = None,
    ) -> Path:
        """Full pipeline: parse -> comply -> generate -> validate -> cost -> visualize -> metadata -> commit.

        Returns the path to the generated element folder.
        """
        t0 = time.time()

        # 1. Parse
        if isinstance(text_or_spec, str):
            spec = self.parse(text_or_spec, context)
        else:
            spec = text_or_spec

        spec_hash = self.hasher.hash_string(_safe_dump(spec))

        # 2. Compliance
        compliance_report = self.check_compliance(spec)

        # 3. Generate
        element_folder = self.generator.generate(spec)

        # 4. Validate
        validation_report = self.validate(element_folder)

        # 5. Cost
        cost_report = self.estimate_cost(element_folder)

        # 6. Visualize (Item 11)
        try:
            self.viz.export(element_folder, format="json3d")
        except Exception:
            logger.debug("Visualization export failed", exc_info=True)

        # 7. Regenerate metadata with real report data
        try:
            generate_metadata(
                element_folder,
                compliance_report=compliance_report,
                cost_report=cost_report,
                validation_report=validation_report,
            )
        except Exception:
            logger.debug("Metadata regeneration failed", exc_info=True)

        # 8. Auto-commit
        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"feat: generate element {spec.ifc_class} ({element_folder.name})",
                )
            except Exception:
                logger.debug("Auto-commit failed for generate", exc_info=True)

        folder_hash = self.hasher.hash_folder(element_folder) if element_folder.is_dir() else ""
        self._audit("system", "generate", str(element_folder), spec_hash, folder_hash)

        duration_ms = (time.time() - t0) * 1000
        self._record_metric("generation", "element_generated", duration_ms)

        return element_folder

    def generate_from_template(
        self,
        template_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> Path:
        """Generate an element from a template with overrides."""
        template_folder = self.library.get_template(template_id)
        if template_folder is None:
            raise FileNotFoundError(f"Template not found: {template_id}")

        t0 = time.time()

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

        duration_ms = (time.time() - t0) * 1000
        self._record_metric("generation", "element_generated", duration_ms, {"template_id": template_id})
        self._record_metric("template", "reuse_count", 1.0, {"template_id": template_id})

        return element_folder

    # -- Validation (Item 09) -------------------------------------------------

    def validate(
        self,
        element_folder: str | Path,
        context: list[str | Path] | None = None,
    ) -> ValidationReport:
        """Validate an element folder."""
        folder = Path(element_folder)
        folder_hash = self.hasher.hash_folder(folder) if folder.is_dir() else ""

        report = self.validator.validate(element_folder, context_elements=context)
        report_hash = self.hasher.hash_string(_safe_dump(report))

        self._audit("system", "validate", str(folder), folder_hash, report_hash)
        status_val = 1.0 if report.status == "valid" else 0.0
        self._record_metric("validation", "validation_completed", status_val)

        return report

    # -- Cost estimation (Item 10) --------------------------------------------

    def estimate_cost(
        self,
        element_folder_or_spec: Any,
        *,
        region: str | None = None,
    ) -> CostReport:
        """Estimate cost and schedule for an element."""
        element_hash = self.hasher.hash_string(str(element_folder_or_spec))
        report = self.cost_engine.estimate(element_folder_or_spec, region=region)
        report_hash = self.hasher.hash_string(_safe_dump(report))

        self._audit("system", "cost_estimate", "", element_hash, report_hash)

        total = getattr(report, "total_cost", 0.0) or 0.0
        self._record_metric("cost", "estimate_completed", float(total))

        return report

    # -- Visualization (Item 11) ----------------------------------------------

    def export_visualization(
        self,
        element_folder: str | Path,
        format: str = "json3d",
    ) -> ExportResult:
        """Export an element to a 3D visualization format."""
        return self.viz.export(element_folder, format=format)

    def generate_viewer(self, element_folder: str | Path) -> Path:
        """Generate an interactive HTML viewer for an element."""
        return self.viz.generate_viewer(element_folder)

    # -- Multi-user sync (Item 12) --------------------------------------------

    def sync(
        self,
        user_id: str = "default",
        role: str = "designer",
    ) -> Any:
        """Fetch remote, detect conflicts, auto-merge if safe."""
        mgr = SyncManager(self.project_root, user_id, role)
        result = mgr.sync()
        self._audit(user_id, "sync_pull", "")
        return result

    def push_changes(
        self,
        message: str,
        user_id: str = "default",
        role: str = "designer",
    ) -> str:
        """Commit and push with conflict check."""
        mgr = SyncManager(self.project_root, user_id, role)
        result = mgr.push_changes(message)
        self._audit(user_id, "sync_push", message)
        return result

    def pull_latest(
        self,
        user_id: str = "default",
        role: str = "designer",
    ) -> Any:
        """Pull latest changes with auto-merge strategy."""
        mgr = SyncManager(self.project_root, user_id, role)
        return mgr.pull_latest()

    def lock_element(
        self,
        element_id: str,
        user_id: str = "default",
        role: str = "designer",
    ) -> LockInfo:
        """Lock an element for exclusive editing."""
        mgr = SyncManager(self.project_root, user_id, role)
        return mgr.lock_element(element_id)

    def unlock_element(
        self,
        element_id: str,
        user_id: str = "default",
        role: str = "designer",
    ) -> bool:
        """Unlock an element."""
        mgr = SyncManager(self.project_root, user_id, role)
        return mgr.unlock_element(element_id)

    # -- Fine-tuning (Item 13) ------------------------------------------------

    def record_feedback(
        self,
        interaction_id: str,
        *,
        correction: dict[str, Any] | None = None,
    ) -> bool:
        """Record feedback on a parser interaction."""
        if correction is not None:
            return self._feedback.record_correction(interaction_id, correction)
        return self._feedback.record_approval(interaction_id)

    def evaluate_parser(self) -> EvaluationReport:
        """Evaluate the current NLP parser against the golden test set."""
        report = self._evaluator.evaluate(self.parser._fallback)
        accuracy = getattr(report, "accuracy", 0.0) or 0.0
        self._record_metric("finetune", "evaluation_completed", float(accuracy))
        return report

    def build_training_dataset(self) -> Path:
        """Build a training dataset from collected interactions."""
        return self._dataset_builder.build_dataset()

    # -- Domain expansion (Item 14) -------------------------------------------

    def list_domains(self) -> list[dict[str, Any]]:
        """List all registered domains."""
        return [
            {
                "name": d.name,
                "description": d.description,
                "ifc_classes": d.ifc_classes,
            }
            for d in self.domain_registry.list_domains()
        ]

    def get_domain_info(self, name: str) -> dict[str, Any] | None:
        """Get detailed info about a specific domain."""
        domain = self.domain_registry.get_domain(name)
        if domain is None:
            return None
        return {
            "name": domain.name,
            "description": domain.description,
            "ifc_classes": domain.ifc_classes,
            "template_count": len(domain.register_templates()),
            "rule_count": len(domain.register_compliance_rules()),
            "parser_pattern_count": len(domain.register_parser_patterns()),
            "cost_entry_count": len(domain.register_cost_data()),
        }

    # -- Regulatory auto-update (Item 15) -------------------------------------

    def check_regulatory_updates(self) -> list[UpdateCheckResult]:
        """Check all regulatory sources for updates."""
        return self._update_monitor.check_all()

    def submit_regulatory_update(
        self,
        code_name: str,
        new_rules: list[dict[str, Any]],
        *,
        new_version: str = "",
    ) -> UpdateReport:
        """Submit a manual regulatory update."""
        # Convert dicts to Rule objects
        parsed_rules = [Rule(**r) for r in new_rules]

        old_rules = self.compliance.get_rules(code_name=code_name)
        source = self._update_monitor.get_source(code_name)
        old_version = source.current_version if source else ""

        diff = self._rule_differ.diff_rules(old_rules, parsed_rules)

        before_hash = self.hasher.hash_string(str([_safe_dump(r) for r in old_rules]))

        update_result = self._rule_updater.apply_update(
            diff, code_name=code_name, version=new_version,
        )

        impact = self._impact_analyzer.analyze(
            diff, library_path=self.library.root,
        )

        report = UpdateReport(
            code_name=code_name,
            old_version=old_version,
            new_version=new_version,
            changes_summary=diff.summary(),
            rules_added=update_result.rules_added,
            rules_modified=update_result.rules_modified,
            rules_removed=update_result.rules_removed,
            affected_templates_count=len(impact.affected_templates),
            affected_elements_count=len(impact.affected_elements),
            git_tag=update_result.git_tag,
        )

        report_path = self.project_root / "REGULATORY_UPDATE.md"
        report_path.write_text(report.to_markdown(), encoding="utf-8")

        self.collaboration.activity.record_event(ActivityEvent(
            type="regulatory_update",
            summary=f"Regulatory update: {code_name} {new_version}",
            details={"code_name": code_name, "changes": diff.summary()},
        ))

        after_hash = self.hasher.hash_string(str([_safe_dump(r) for r in parsed_rules]))
        self._audit("system", "regulatory_update", code_name, before_hash, after_hash)

        if self.auto_commit:
            try:
                commit_all(
                    self.repo,
                    message=f"regulatory: update {code_name} to {new_version}",
                )
            except Exception:
                logger.debug("Auto-commit failed for regulatory update", exc_info=True)

        return report

    # -- Collaboration (Item 16) ----------------------------------------------

    def add_comment(
        self,
        element_id: str,
        user: str,
        text: str,
        reply_to: str | None = None,
    ) -> Comment:
        """Add a comment to an element."""
        comment = self.collaboration.add_comment(element_id, user, text, reply_to)
        self._audit(user, "collab_comment", element_id)
        self._record_metric("collaboration", "comment_added", 1.0, user=user)
        return comment

    def get_comments(self, element_id: str) -> list[Comment]:
        """Get all comments for an element."""
        return self.collaboration.get_comments(element_id)

    def create_task(
        self,
        title: str,
        assignee: str,
        element_id: str = "",
        due_date: datetime | None = None,
        priority: str = "normal",
    ) -> Task:
        """Create a collaboration task."""
        task = self.collaboration.create_task(title, assignee, element_id, due_date, priority)
        self._audit(assignee, "collab_task_create", element_id)
        return task

    def get_tasks(
        self,
        assignee: str | None = None,
        status: str | None = None,
        element_id: str | None = None,
    ) -> list[Task]:
        """Get tasks with optional filtering."""
        return self.collaboration.get_tasks(assignee, status, element_id)

    def request_review(
        self,
        element_id: str,
        reviewer: str,
        notes: str | None = None,
    ) -> Review:
        """Request a review for an element."""
        review = self.collaboration.request_review(element_id, reviewer, notes)
        self._audit(reviewer, "collab_review_request", element_id)
        return review

    def approve_review(
        self,
        review_id: str,
        reviewer: str,
        comments: str | None = None,
    ) -> Review | None:
        """Approve a review."""
        review = self.collaboration.approve_review(review_id, reviewer, comments)
        if review:
            self._audit(reviewer, "collab_review_approve", review.element_id)
            self._record_metric("collaboration", "review_approved", 1.0, user=reviewer)
        return review

    def reject_review(
        self,
        review_id: str,
        reviewer: str,
        reason: str,
    ) -> Review | None:
        """Reject a review with reason."""
        review = self.collaboration.reject_review(review_id, reviewer, reason)
        if review:
            self._audit(reviewer, "collab_review_reject", review.element_id)
        return review

    def get_activity_feed(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get the activity feed."""
        return self.collaboration.get_activity_feed(since=since, limit=limit)

    def execute_command(self, text: str, user: str = "") -> str:
        """Execute a natural-language command via the bot provider."""
        return self.collaboration.execute_command(text, user=user)

    # -- Security & Audit (Item 17) -------------------------------------------

    def get_audit_log(
        self,
        resource: str | None = None,
        user: str | None = None,
        since: str | None = None,
    ) -> list[AuditEntry]:
        """Query the audit log."""
        return self.audit_logger.get_log(resource=resource, user=user, since=since)

    def verify_audit_chain(self) -> bool:
        """Validate the entire audit hash chain."""
        return self.audit_logger.verify_chain()

    def scan_security(self, project_path: str | Path | None = None) -> SecurityReport:
        """Run a full security scan."""
        path = Path(project_path) if project_path else self.project_root
        report = self.security_scanner.scan_all(path)
        report_hash = self.hasher.hash_string(report.to_json())
        self._audit("system", "security_scan", str(path), "", report_hash)
        self._record_metric(
            "security", "scan_completed",
            float(len(report.findings)),
        )
        return report

    def encrypt_element(self, element_id: str, key: bytes) -> list[Path]:
        """Encrypt an element folder."""
        folder = self.project_root / "elements" / f"element_{element_id}"
        return self.encryption.encrypt_folder(folder, key, patterns=[".json", ".ifc"])

    def decrypt_element(self, element_id: str, key: bytes) -> list[Path]:
        """Decrypt an element folder."""
        folder = self.project_root / "elements" / f"element_{element_id}"
        decrypted: list[Path] = []
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".ifc"):
                self.encryption.decrypt_file(f, key)
                decrypted.append(f)
        return decrypted

    # -- Deployment (Item 18) -------------------------------------------------

    def package_system(self, output_path: str | Path) -> Path:
        """Package the AEC OS project for distribution."""
        return self._packager.package(self.project_root, output_path)

    def check_health(self) -> HealthReport:
        """Run health checks on the installation."""
        return self._health_checker.check(self.project_root)

    def create_snapshot(self, label: str) -> dict[str, Any]:
        """Create a rollback snapshot."""
        return self._rollback_manager.create_snapshot(label)

    def rollback(self, label: str) -> bool:
        """Rollback to a snapshot."""
        return self._rollback_manager.rollback(label)

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List available rollback snapshots."""
        return self._rollback_manager.list_snapshots()

    def generate_dockerfile(self) -> Path:
        """Generate a Dockerfile for the project."""
        return self._docker_builder.generate_dockerfile(self.project_root)

    def generate_ci_config(self) -> Path:
        """Generate GitHub Actions CI workflow."""
        return self._ci_generator.generate_github_actions(self.project_root)

    # -- Analytics (Item 19) --------------------------------------------------

    def get_metrics(
        self,
        module: str,
        event_type: str,
        period: str = "month",
    ) -> list[tuple[str, float]]:
        """Get aggregated metric data."""
        return self._warehouse.aggregate(module, event_type, period)

    def get_kpis(self) -> dict[str, Any]:
        """Get all KPIs from Bible Section 8."""
        return self._kpi.all_kpis()

    def generate_dashboard(self) -> Path:
        """Generate an HTML analytics dashboard."""
        return self._dashboard_gen.generate_html(self.project_root)

    def export_analytics(self, format: str = "json") -> str:
        """Export analytics in the given format."""
        kpis = self._kpi.all_kpis()
        if format == "csv":
            events = self.metrics.get_events()
            path = self.project_root / "ANALYTICS.csv"
            self._report_exporter.export_csv(events, path)
            return str(path)
        elif format == "markdown":
            return self._report_exporter.export_markdown(kpis)
        else:
            return self._report_exporter.export_json(kpis)

    # -- Direct VCS access ----------------------------------------------------

    def commit(self, message: str) -> str:
        """Create a manual commit of all pending changes."""
        return commit_all(self.repo, message)

    def status(self) -> str:
        """Return the git status (porcelain format)."""
        return self.repo.status()

    def is_clean(self) -> bool:
        """Return *True* if the working tree has no uncommitted changes."""
        return self.repo.is_clean()
