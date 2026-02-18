**Data Extraction Pipeline (Roadmap Item 1)**  
**Goal:** Convert any Revit-exported IFC into a lossless, editable folder tree where every individual designed item (wall, door, MEP run, etc.) lives in its own folder with subfolders for geometry, properties, materials, relationships, costs, and a Markdown summary. Output is pure files—no database required—so you can git it, template it, and feed it to LLMs later.

**Output Structure (per project)**
```
templates/
└── {project_guid}/
    ├── metadata.json          # project/site/building info
    ├── spatial/
    │   └── {site_guid}/
    │       └── {building_guid}/
    │           └── {storey_guid}/
    │               └── {space_guid}/
    └── elements/
        └── IfcWall/
            └── {global_id}_6in_concrete_fire2hr/
                ├── metadata.json      # name, type, GUID, IFC class
                ├── geometry.json      # placement, vertices (or .obj)
                ├── properties/
                │   ├── Pset_WallCommon.json
                │   └── Pset_FireRating.json
                ├── materials/
                │   └── concrete.json
                ├── relationships/
                │   └── connects_to.json
                ├── quantities.json
                └── README.md          # human summary + code snippet
```

### Prerequisites (30 min)
- Python 3.11+
- `pip install ifcopenshell pandas tqdm`
- Git repo: `aec-os-extractor`
- Sample IFCs: download Duplex or your own Revit exports

### Phase 1: Core Loader (Day 1)
1. Create `pipeline/extract.py`
2. Load & validate:
   ```python
   import ifcopenshell
   from pathlib import Path
   import json
   from tqdm import tqdm

   def load_ifc(path: Path):
       model = ifcopenshell.open(str(path))
       ifcopenshell.validate(model)  # catches basic errors
       return model
   ```

### Phase 2: Entity Extraction (Day 1-2)
3. Recursive dict converter (handles references cleanly):
   ```python
   def entity_to_dict(entity, model, depth=0):
       if depth > 5: return {"ref": entity.GlobalId}  # prevent recursion explosion
       info = entity.get_info(recursive=False)
       # Add psets, qsets, material
       info["psets"] = ifcopenshell.util.element.get_psets(entity)
       info["quantities"] = ifcopenshell.util.element.get_quantities(entity)
       info["material"] = ifcopenshell.util.element.get_material(entity)
       return info
   ```

4. Bulk extract all elements:
   ```python
   for ifc_class in ["IfcWall", "IfcDoor", "IfcBeam", ...]:  # or just "IfcElement"
       for entity in model.by_type(ifc_class):
           data = entity_to_dict(entity, model)
           save_to_folder(entity, data)
   ```

### Phase 3: Folder & File Writer (Day 2)
5. Build spatial hierarchy first (using IfcRelAggregates / IfcRelContainedInSpatialStructure):
   - Start at IfcProject → recurse down to spaces.
   - Create folders with GUID names for traceability.

6. Per-element folder writer:
   ```python
   def save_element(entity, data, root: Path):
       folder = root / "elements" / entity.is_a() / f"{entity.GlobalId}_{entity.Name or 'unnamed'}"
       folder.mkdir(parents=True, exist_ok=True)
       
       (folder / "metadata.json").write_text(json.dumps(data, indent=2, default=str))
       (folder / "README.md").write_text(generate_markdown_summary(data))
       
       # geometry (light version first)
       if hasattr(entity, "Representation"):
           geom_folder = folder / "geometry"
           geom_folder.mkdir(exist_ok=True)
           # optional: use ifcopenshell.geom to export vertices to JSON
   ```

7. Auto-generate README.md (short, dense):
   ```
   # IfcWall {GlobalId}
   Type: Standard Wall
   Fire rating: 2hr
   Thickness: 150mm
   Compliant with: CBC 2025
   Last extracted: 2026-02-17
   ```

### Phase 4: Full Pipeline Script (Day 3)
```python
def run_pipeline(ifc_path: Path, output_root: Path):
    model = load_ifc(ifc_path)
    project = model.by_type("IfcProject")[0]
    root = output_root / project.GlobalId
    root.mkdir(parents=True, exist_ok=True)
    
    extract_spatial_hierarchy(model, root)
    extract_all_elements(model, root)
    print(f"✅ Extracted {len(list(root.rglob('*.json')))} files")
```

### Phase 5: Quality & Safety (Day 4)
- Error handling: wrap every entity in try/except; log skipped items to `errors.log`
- Duplicates: use GUID as unique key
- Large files: add `--max-elements 5000` flag + tqdm progress
- Geometry toggle: `--geometry` flag (heavy; uses ifcopenshell.geom)
- Validation: after extraction, run `ifcdiff` on a reconstructed tiny IFC (later step)

### Phase 6: Testing & Iteration (Day 5)
- Test files: 3 small + 1 real Revit IFC
- Metrics: count folders == count elements in IFC
- Round-trip check: re-import JSON subset back to new IFC (using ifcopenshell.api) – aim for 95% match on properties
- Run on 10 different Revit exports; fix schema differences (IFC2X3 vs IFC4)

### Phase 7: Automation & Scaling (Ongoing)
- CLI: `python -m pipeline extract myfile.ifc --out templates/`
- GitHub Action: auto-run on push of new IFC
- For 10k+ element models: multiprocessing.Pool or Dask
- Store geometry separately if >500 MB

**Total time to working v1:** 5-7 days (you already have the seed script).  
**Maintenance:** Update once per year for new IFC4.3 features; ifcopenshell stays current.

This pipeline is now the single source of truth. Every later roadmap item (templates, LLM parser, compliance engine) reads directly from these folders.

Run the skeleton on one file today and paste the folder tree output here—I’ll debug the next chunk with you instantly.