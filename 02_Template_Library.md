**Template Library (Roadmap Item 2)**  
**Goal:** Create a git-versioned, searchable collection of 100+ standardized, single-element (or small assembly) IFC templates. Each is a ready-to-drop building block that matches your extraction pipeline’s folder format exactly. Templates are pre-tagged for type, material, performance, code compliance, and region—so later roadmap steps (NLP parser, compliance engine) can find and insert them instantly.  

**Output Structure (root of your `aec-os` repo)**  
```
library/
├── index.json                    # master searchable index
├── architectural/
│   ├── walls/
│   │   └── concrete_150mm_fire2hr_ca_2025/
│   │       ├── template.ifc          # clean single-element IFC (IFC4.3 preferred)
│   │       ├── metadata.json         # core props + tags
│   │       ├── geometry/             # .obj or JSON vertices (optional)
│   │       ├── properties/           # standardized Psets
│   │       ├── README.md
│   │       └── tags.json
│   ├── doors/
│   └── ...
├── structural/
├── mep/
├── interiors/
├── site/
└── scripts/
    └── curate.py                     # all automation
```

**Prerequisites (1 hour)**  
- Item 1 pipeline complete  
- `pip install ifcopenshell pandas tqdm`  
- Git + Git LFS (for .ifc files)  
- 5–10 real Revit IFC exports + internet for public sources  

**Phase 1: Define Standards (Day 1)**  
1. Create `library/scripts/schema.py` with required fields:  
   ```python
   TEMPLATE_SCHEMA = {
       "ifc_class": str,
       "name": str,
       "version": "1.0",
       "region": list,          # ["CA", "US", "EU"]
       "compliance": list,      # ["IBC2024", "CBC2025", "Title24"]
       "performance": dict,     # {"fire_rating": "2hr", "acoustic": "STC45", ...}
       "typical_use": list,
       "last_updated": "2026-02-17"
   }
   ```  
2. Naming convention: `{material}_{thickness}_{key_perf}_{region}_v{num}`  
3. Decide IFC schema: default IFC4.3.2.0 (latest as of Feb 2026).  

**Phase 2: Seed from Your Own Projects (Day 1)**  
Run your extraction pipeline on past Revit → IFC files.  
Script `scripts/seed_from_extraction.py`:  
```python
for element_folder in Path("extracted/...").glob("**/*"):
    if is_good_template(element_folder):  # size, completeness check
        copy_and_clean(element_folder, library_target)
```  
Deduplicate using hash of geometry bounding box + key properties.  

**Phase 3: Add Public & Manufacturer Sources (Day 2)**  
Download and standardize:  
- buildingSMART official samples: https://github.com/buildingSMART/Sample-Test-Files  
- buildingSMART community samples: https://github.com/buildingsmart-community/Community-Sample-Test-Files  
- BIMobject.com (free IFC downloads – filter “IFC”)  
- ARCAT BIM Library (export to IFC where available)  
- BIMsmith Market, Bimstore, MEPcontent, Modlar IFC section  
Script `scripts/import_public.py` that downloads, runs through your extraction pipeline, then cleans.  

**Phase 4: Clean & Standardize (Day 2–3)**  
Use ifcopenshell.api to:  
- Remove project-specific data (site coords, owner history)  
- Reset GlobalIds  
- Normalize units to SI  
- Add missing standard Psets (Pset_WallCommon, Pset_FireRating, etc.)  
Example:  
```python
import ifcopenshell.api as api
model = ifcopenshell.open("raw.ifc")
wall = model.by_type("IfcWall")[0]
api.run("attribute.edit_attributes", model, product=wall, attributes={"Name": "Standard 150mm Concrete Wall"})
api.run("pset.add_pset", model, product=wall, name="Pset_FireRating")
# ... set values
model.write("clean_template.ifc")
```  

**Phase 5: Enrich & Tag (Day 3–4)**  
Auto-generate:  
- `metadata.json` + `tags.json`  
- Dense README.md (same format as extraction)  
Manual review for first 50 (you’ll get fast).  
Build master index:  
```python
df = pd.DataFrame(all_templates)
df.to_json("library/index.json", orient="records", indent=2)
```  

**Phase 6: Search & Validation Tools (Day 4)**  
Add to `scripts/library.py`:  
```python
def find_templates(query: dict) -> list:
    # e.g. {"ifc_class": "IfcWall", "performance.fire_rating": "2hr", "region": "CA"}
    return [t for t in index if matches(t, query)]
```  
Validation:  
- Load template.ifc in Revit (or free BIMvision) → export → diff with original  
- Geometry integrity check  
- Property completeness score  

**Phase 7: Version Control & Maintenance (Day 5 + ongoing)**  
- Conventional commits: `feat(wall): add gypsum_interior_100mm_us`  
- GitHub Action: on push → run validation suite  
- Deprecation: move old versions to `archive/`  
- Annual sweep: update compliance tags when codes change  

**Total time to working v1 (100 templates):** 5–7 days  
**Milestone check:** You can run `python -m scripts.library find --class IfcWall --fire 2hr --region CA` and get 5+ ready templates instantly.  

This library is now the heart of your system. Every new element you extract or design gets added here automatically.  

Run Phase 1–2 today and drop the first 10 folder names here—I’ll give you the exact curate.py code to finish the rest tomorrow.