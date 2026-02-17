"""AEC OS — AI-assisted operating system for architecture, engineering, and construction."""

__version__ = "0.3.0"

from aecos.api.facade import AecOS
from aecos.extraction.pipeline import ifc_to_element_folders
from aecos.metadata.generator import generate_metadata
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags
from aecos.vcs.repo import RepoManager

__all__ = [
    "__version__",
    "AecOS",
    "ifc_to_element_folders",
    "generate_metadata",
    "TemplateLibrary",
    "TemplateTags",
    "RepoManager",
]
