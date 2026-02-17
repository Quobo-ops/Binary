**Python API Wrapper (Roadmap Item 5)**  
**Goal:** To develop a centralized, installable Python package that provides a clean, consistent, and extensible application programming interface for all prior components. The wrapper unifies operations on IFC files (via ifcopenshell), the template library (Item 2), extracted project structures (Item 1), and Markdown metadata generation (Item 3). It supports full CRUD functionality (Create, Read, Update, Delete) on individual elements and assemblies, while serving as the foundation for later roadmap items such as natural-language parsing (Item 6) and compliance checking (Item 7).

**Package Name and Structure**  
The package shall be named `aecos` (AEC Operating System) and installed via `pip install -e .` for development. Recommended directory layout:  
```
aecos/
├── __init__.py                    # Exposes public API
├── config.py                      # Project paths and settings
├── core/
│   ├── extractor.py               # Wraps Item 1 pipeline
│   ├── library.py                 # Template search and loading
│   ├── markdown.py                # Wraps Item 3 generation
│   └── validator.py               # Schema and integrity checks
├── models/
│   └── element.py                 # Pydantic data models for type safety
├── revit/
│   └── integration.py             # pyRevit and RevitPythonShell hooks
├── utils/
│   ├── converters.py              # JSON ↔ IFC transformations
│   └── helpers.py                 # Common utilities
├── cli.py                         # Command-line interface
├── pyproject.toml                 # Build and dependency specification
└── README.md                      # Package documentation
```

**Prerequisites (45 minutes)**  
- Python 3.11 or higher  
- Completion of Roadmap Items 1–4  
- `pip install ifcopenshell pydantic pandas tqdm jinja2`  
- pyRevit installed (for Revit-native scripting; external scripts may use RevitPythonShell or ironpython)  
- Git repository from Item 4  

**Phase 1: Package Initialization and Configuration (Day 1)**  
1. Create the directory structure and `pyproject.toml` with dependencies.  
2. Define centralized paths in `config.py`:  
   ```python
   from pathlib import Path
   LIBRARY_ROOT = Path.home() / "aec-os" / "library"
   EXTRACTED_ROOT = Path.home() / "aec-os" / "extracted"
   ```  
3. Implement basic logging and error handling using the standard `logging` module.  

**Phase 2: Data Models (Day 1)**  
Create Pydantic models in `models/element.py` for strict validation:  
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ElementMetadata(BaseModel):
    ifc_class: str
    global_id: str
    name: str
    region: List[str]
    compliance: List[str]
    performance: Dict[str, str]
    last_updated: str = Field(default_factory=lambda: "2026-02-17")
```

**Phase 3: Core Extractor and Library Modules (Day 2)**  
Wrap Item 1 and Item 2:  
- `core/extractor.py`: `def extract_ifc(ifc_path: Path, output_dir: Path) -> int` (returns element count).  
- `core/library.py`:  
  ```python
  def search_templates(filters: Dict) -> List[Path]:
      # e.g., {"ifc_class": "IfcWall", "performance.fire_rating": "2hr"}
  def load_template(template_path: Path) -> ifcopenshell.file:
      return ifcopenshell.open(str(template_path / "template.ifc"))
  ```  

**Phase 4: Markdown and Validation Integration (Day 2–3)**  
Reuse and expose Item 3:  
- `core/markdown.py`: `def generate_markdown(element_folder: Path) -> None`  
- `core/validator.py`: Comprehensive checks for GUID uniqueness, property completeness, and geometry integrity.  

**Phase 5: CRUD Operations and Revit Integration (Day 3–4)**  
Implement high-level functions:  
- `create_element(ifc_class: str, parameters: Dict) -> Path` (generates new IFC chunk from template)  
- `update_element(element_folder: Path, updates: Dict)`  
- `delete_element(element_folder: Path)` (with git-safe archiving)  
- Revit bridge in `revit/integration.py` for direct insertion via pyRevit scripts.  

**Phase 6: Command-Line Interface and Documentation (Day 4)**  
Develop `cli.py` using `typer` or `argparse`:  
```bash
aecos extract myfile.ifc --output extracted/project123
aecos search --class IfcWall --fire 2hr --region CA
```  
Include comprehensive docstrings and a Sphinx-compatible README.

**Phase 7: Testing, Packaging, and CI Integration (Day 5)**  
- Unit tests (pytest) covering 90 % of public API.  
- Integration tests using sample IFC files from Item 2.  
- GitHub Actions workflow to run tests on push.  
- Package distribution: `pip install .` or publish to private PyPI if desired.  

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After installation, the following commands must execute successfully and produce expected outputs:  
`python -m aecos extract sample.ifc --output test_output`  
`python -m aecos search --class IfcWall --fire 2hr`  

The resulting wrapper constitutes a stable foundation that abstracts all file-system and IFC complexities, allowing subsequent roadmap items to interact with the system through simple function calls rather than direct file operations.  

I recommend beginning with Phases 1 through 3 to establish the package skeleton. Should you encounter any implementation challenges or require sample code for a specific module, please provide the relevant details for targeted assistance.