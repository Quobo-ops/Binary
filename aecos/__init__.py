"""AEC OS — AI-assisted operating system for architecture, engineering, and construction."""

__version__ = "0.5.0"

from aecos.api.facade import AecOS
from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.report import ComplianceReport
from aecos.cost.engine import CostEngine
from aecos.cost.report import CostReport
from aecos.extraction import ifc_to_element_folders
from aecos.generation.assembly import AssemblyGenerator
from aecos.generation.generator import ElementGenerator
from aecos.metadata.generator import generate_metadata
from aecos.nlp.parser import NLParser
from aecos.nlp.schema import ParametricSpec
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags
from aecos.validation.report import ValidationReport
from aecos.validation.validator import Validator
from aecos.vcs.repo import RepoManager

__all__ = [
    "__version__",
    "AecOS",
    "AssemblyGenerator",
    "ComplianceEngine",
    "ComplianceReport",
    "CostEngine",
    "CostReport",
    "ElementGenerator",
    "NLParser",
    "ParametricSpec",
    "TemplateLibrary",
    "TemplateTags",
    "ValidationReport",
    "Validator",
    "ifc_to_element_folders",
    "generate_metadata",
    "RepoManager",
]
