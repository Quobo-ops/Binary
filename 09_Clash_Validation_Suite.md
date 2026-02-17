**Clash & Validation Suite (Roadmap Item 9)**  
**Goal:** Establish a fully automated, extensible validation and clash-detection module within the `aecos` package that performs geometric, topological, semantic, and constructability checks on newly generated elements (Item 8), extracted data (Item 1), or full assemblies before they are committed to the template library or project repository. The suite replicates essential capabilities of commercial tools such as Solibri Model Checker while remaining lightweight, local, and integrated with the existing pipeline, ensuring every element satisfies spatial coordination, clearance requirements, code-derived constraints (Item 7), and library standards (Item 2).  

**Output Products**  
- JSON validation report (machine-readable)  
- Markdown summary (`VALIDATION.md`) appended to the element folder  
- Optional visual export (highlighted clashes in Speckle or simple OBJ preview)  

**Integration Points**  
- Called automatically at the end of `aecos.core.generator.generate_element()`  
- Accepts context models (existing project IFC) for clash detection  
- Feeds results directly into Markdown Metadata Layer (Item 3) and Version Control Backbone (Item 4)  

**Prerequisites (45 minutes)**  
- Roadmap Items 1–8 completed and `aecos` package installed in editable mode  
- `pip install ifcopenshell numpy scipy shapely trimesh` (for geometry operations and mesh intersection)  
- Optional: Git LFS already configured for large geometry files  

**Phase 1: Validation Framework and Rule Registry (Day 1)**  
Create `aecos/validation/core.py` with a central `Validator` class:  
```python
from pydantic import BaseModel
from typing import List, Dict
import ifcopenshell

class ValidationRule(BaseModel):
    name: str
    description: str
    severity: str  # "error", "warning", "info"
    applicable_classes: List[str]

class Validator:
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.load_default_rules()

    def validate(self, element_folder: Path, context_model: ifcopenshell.file = None) -> Dict:
        results = {"status": "passed", "issues": []}
        # Run geometric, semantic, topological checks
        return results
```

**Phase 2: Geometric Clash Detection (Day 1–2)**  
Tessellate elements using `ifcopenshell.geom` and perform efficient clash checks:  
```python
import ifcopenshell.geom
from shapely.geometry import Polygon
from scipy.spatial import KDTree

def detect_clashes(new_element_model: ifcopenshell.file, context_model: ifcopenshell.file, tolerance_mm: float = 10):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)
    
    new_triangles = ifcopenshell.geom.create_shape(settings, new_element_model)
    context_triangles = ifcopenshell.geom.create_shape(settings, context_model)
    
    # Build KDTree for fast proximity queries
    tree = KDTree(context_triangles.vertices)
    clashes = []
    for i, pt in enumerate(new_triangles.vertices):
        dist, idx = tree.query(pt)
        if dist < tolerance_mm / 1000.0:
            clashes.append({"point": pt.tolist(), "distance_mm": dist * 1000})
    return clashes
```

**Phase 3: Semantic and Topological Validation (Day 2)**  
- Property consistency against library templates  
- Required relationships (e.g., wall must connect to slab)  
- Clearance rules (e.g., door swing space, MEP corridor width)  
Implement via reusable rule functions registered in the `Validator`.

**Phase 4: Full Validation Pipeline (Day 3)**  
```python
def run_full_validation(spec: ParametricSpec, generated_folder: Path, context_ifc: Path = None):
    validator = Validator()
    report = validator.validate(generated_folder, context_ifc)
    
    if report["status"] == "failed":
        # Auto-suggest compliant alternatives from library (Item 2)
        alternatives = aecos.core.library.find_alternatives(spec)
        report["suggested_fixes"] = alternatives
    
    aecos.core.markdown.generate_validation_report(generated_folder, report)
    return report
```

**Phase 5: Reporting and Auto-Documentation (Day 3–4)**  
- Generate `VALIDATION.md` with tables of issues, severity, and remediation steps  
- Append compliance status from Item 7  
- Store full JSON report for audit trail in git  

**Phase 6: CLI and Revit Integration (Day 4)**  
```bash
aecos validate generated/wall_123 --context project_model.ifc --tolerance 5mm
```
pyRevit ribbon button: “Validate Selection” that exports selected elements to IFC, runs the suite, and highlights clashes in Revit view.

**Phase 7: Testing, Benchmarking, and Maintenance (Day 5)**  
- Test suite: 120 known clash scenarios (intersection, clearance violation, missing connection)  
- Performance target: < 4 seconds per element on typical hardware  
- Accuracy target: 99 % detection rate on geometric clashes  
- Annual rule updates via git-tracked `rules/` directory  

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Executing `aecos validate generated/element_folder --context existing_project.ifc` produces a complete validation report confirming zero critical issues, with any warnings clearly documented in `VALIDATION.md` and automatically committed to the repository via the Version Control Backbone.

This suite transforms the system into a proactive quality gate, preventing downstream coordination errors and enabling confident scaling to full-building generation.  

Implement Phases 1–3 today on a single element type (e.g., IfcWall) using one of your existing generated folders. Should any questions arise regarding tessellation settings or rule definitions, furnish the relevant details for immediate refinement.
