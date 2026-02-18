"""AEC OS — AI-assisted operating system for architecture, engineering, and construction."""

__version__ = "1.0.0"

from aecos.analytics.collector import MetricsCollector
from aecos.analytics.dashboard import DashboardGenerator
from aecos.analytics.exporter import ReportExporter
from aecos.analytics.kpi import KPICalculator
from aecos.analytics.warehouse import DataWarehouse
from aecos.api.facade import AecOS
from aecos.collaboration.manager import CollaborationManager
from aecos.collaboration.models import ActivityEvent, Comment, Review, Task
from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.report import ComplianceReport
from aecos.cost.engine import CostEngine
from aecos.cost.report import CostReport
from aecos.deployment.ci import CIGenerator
from aecos.deployment.config_manager import ConfigManager
from aecos.deployment.docker import DockerBuilder
from aecos.deployment.health import CheckResult, HealthChecker, HealthReport
from aecos.deployment.installer import InstallResult, Installer
from aecos.deployment.packager import SystemPackager
from aecos.deployment.rollback import RollbackManager
from aecos.domains.base import DomainPlugin
from aecos.domains.registry import DomainRegistry
from aecos.extraction import ifc_to_element_folders
from aecos.finetune.collector import InteractionCollector
from aecos.finetune.dataset import DatasetBuilder
from aecos.finetune.evaluator import EvaluationReport, ModelEvaluator
from aecos.finetune.feedback import FeedbackManager
from aecos.finetune.trainer import TrainingManager
from aecos.generation.assembly import AssemblyGenerator
from aecos.generation.generator import ElementGenerator
from aecos.metadata.generator import generate_metadata
from aecos.nlp.parser import NLParser
from aecos.nlp.schema import ParametricSpec
from aecos.regulatory.differ import RuleDiffer, RuleDiffResult
from aecos.regulatory.monitor import UpdateCheckResult, UpdateMonitor
from aecos.regulatory.report import UpdateReport
from aecos.regulatory.updater import RuleUpdater
from aecos.security.audit import AuditEntry, AuditLogger
from aecos.security.encryption import EncryptionManager
from aecos.security.hasher import Hasher
from aecos.security.policies import SecurityPolicy
from aecos.security.rbac import check_permission, require_role
from aecos.security.report import Finding, SecurityReport
from aecos.security.scanner import SecurityScanner
from aecos.sync.conflict import ConflictResult
from aecos.sync.manager import SyncManager
from aecos.sync.permissions import PermissionManager, Role
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags
from aecos.validation.report import ValidationReport
from aecos.validation.validator import Validator
from aecos.vcs.repo import RepoManager
from aecos.visualization.bridge import ExportResult, VisualizationBridge
from aecos.visualization.scene import Scene

__all__ = [
    "__version__",
    # Facade
    "AecOS",
    # Security (Item 17)
    "AuditEntry",
    "AuditLogger",
    "EncryptionManager",
    "Finding",
    "Hasher",
    "SecurityPolicy",
    "SecurityReport",
    "SecurityScanner",
    "check_permission",
    "require_role",
    # Deployment (Item 18)
    "CIGenerator",
    "CheckResult",
    "ConfigManager",
    "DockerBuilder",
    "HealthChecker",
    "HealthReport",
    "InstallResult",
    "Installer",
    "RollbackManager",
    "SystemPackager",
    # Analytics (Item 19)
    "DashboardGenerator",
    "DataWarehouse",
    "KPICalculator",
    "MetricsCollector",
    "ReportExporter",
    # Items 01-16
    "ActivityEvent",
    "AssemblyGenerator",
    "CollaborationManager",
    "Comment",
    "ComplianceEngine",
    "ComplianceReport",
    "ConflictResult",
    "CostEngine",
    "CostReport",
    "DatasetBuilder",
    "DomainPlugin",
    "DomainRegistry",
    "ElementGenerator",
    "EvaluationReport",
    "ExportResult",
    "FeedbackManager",
    "InteractionCollector",
    "ModelEvaluator",
    "NLParser",
    "ParametricSpec",
    "PermissionManager",
    "RepoManager",
    "Review",
    "Role",
    "RuleDiffer",
    "RuleDiffResult",
    "RuleUpdater",
    "Scene",
    "SyncManager",
    "Task",
    "TemplateLibrary",
    "TemplateTags",
    "TrainingManager",
    "UpdateCheckResult",
    "UpdateMonitor",
    "UpdateReport",
    "ValidationReport",
    "Validator",
    "VisualizationBridge",
    "ifc_to_element_folders",
    "generate_metadata",
]
