"""AEC OS — AI-assisted operating system for architecture, engineering, and construction."""

__version__ = "0.4.0"

from aecos.api.facade import AecOS
from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.report import ComplianceReport
from aecos.extraction.pipeline import ifc_to_element_folders
from aecos.metadata.generator import generate_metadata
from aecos.nlp.parser import NLParser
from aecos.nlp.schema import ParametricSpec
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags
from aecos.vcs.repo import RepoManager

__all__ = [
    "__version__",
    "AecOS",
    "ComplianceEngine",
    "ComplianceReport",
    "NLParser",
    "ParametricSpec",
    "ifc_to_element_folders",
    "generate_metadata",
    "TemplateLibrary",
    "TemplateTags",
    "RepoManager",
]
