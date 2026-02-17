**Markdown Metadata Layer (Roadmap Item 3)**  
**Goal:** Turn every folder created by the extraction pipeline (Item 1) and every template (Item 2) into a human-first knowledge base. Auto-generate short, dense, version-controlled Markdown files (primarily `README.md`, plus optional `COMPLIANCE.md`, `USAGE.md`, `COST.md`) that LLMs, teammates, and future roadmap steps can read instantly. No more hunting through JSON—open the folder and see exactly what the element is, why it complies, and how to use it.

**Final Folder Structure (per element)**
```
elements/IfcWall/{globalid}_150mm_concrete_fire2hr_ca/
├── README.md              # 1-page human summary (always present)
├── COMPLIANCE.md          # code citations + links
├── USAGE.md               # Python/Revit/Dynamo snippets
├── COST.md                # pricing + sources (optional)
├── metadata.json
├── properties/
├── geometry/
└── tags.json
```

**Example README.md (exactly 20–40 lines)**
```markdown
# 150 mm Concrete Wall – 2 hr Fire Rated (California)

**IFC Class:** IfcWallStandardCase  
**Name:** W-EXT-01  
**GUID:** 3f8a9b2c-...  
**Extracted:** 2026-02-17  

**Key Specs**  
- Thickness: 150 mm  
- Fire rating: 2 hours (ASTM E119)  
- Thermal resistance: R-15  
- Acoustic: STC 52  
- Typical use: Exterior load-bearing  

**Compliance**  
- CBC 2025 §703.3.2  
- IBC 2024 Table 721.1(2)  
- Title 24 Part 6 (energy) – compliant when paired with R-20 insulation  

**Links**  
- [CBC 2025 PDF](https://codes.iccsafe.org/content/CBC2025P2/chapter-7-fire-resistance-rated-construction)  
- [Manufacturer test report](https://example.com/concrete-wall-test.pdf)  

**Quick Insert (pyRevit)**
```python
from aecos import load_template
wall = load_template("library/architectural/walls/concrete_150mm_fire2hr_ca")
```

Last updated: 2026-02-17 | Status: Approved
```

### Prerequisites (30 min)
- Item 1 & 2 complete  
- `pip install jinja2 pyyaml markdown2`  
- Folder: `library/scripts/markdown_layer.py`

### Phase 1: Template System (Day 1)
Create `templates/markdown/` with Jinja2 files:
- `readme.j2`
- `compliance.j2`
- `usage.j2`

Example `readme.j2` snippet:
```jinja
# {{ element.name }} – {{ element.performance.fire_rating }} Fire Rated

**IFC Class:** {{ element.ifc_class }}
**Region:** {{ element.region | join(', ') }}

{% for k, v in element.performance.items() %}
- {{ k|title }}: {{ v }}
{% endfor %}
```

### Phase 2: Core Generator (Day 1–2)
```python
import jinja2
from pathlib import Path
import json

env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/markdown"))

def generate_markdown(element_folder: Path):
    meta = json.loads((element_folder / "metadata.json").read_text())
    
    # README
    template = env.get_template("readme.j2")
    (element_folder / "README.md").write_text(
        template.render(element=meta, date="2026-02-17")
    )
    
    # COMPLIANCE
    if "compliance" in meta:
        comp_template = env.get_template("compliance.j2")
        (element_folder / "COMPLIANCE.md").write_text(
            comp_template.render(rules=meta["compliance"])
        )
```

Hook to Item 1:
```python
# In your extraction pipeline, at the end of save_element():
generate_markdown(folder)
```

### Phase 3: Auto-Links & Enrichment (Day 2)
Add smart links:
- Code sections → direct URLs (IBC, CBC, Eurocode)
- Manufacturer data (BIMobject, ARCAT) via simple lookup table in `library/references.json`
- Git blame / history link for audit

Script snippet:
```python
def enrich_compliance(meta):
    rules = meta.get("compliance", [])
    for rule in rules:
        if "CBC" in rule:
            rule["link"] = f"https://codes.iccsafe.org/content/CBC2025P2/chapter-{rule['chapter']}"
    return rules
```

### Phase 4: Batch & Maintenance Tools (Day 3)
CLI:
```bash
python -m scripts.markdown_layer generate --folder templates/library --all
python -m scripts.markdown_layer update --folder extracted/2026-project --codes-only
```

GitHub Action (`.github/workflows/md-update.yml`):
- On push to `library/` or `extracted/` → regenerate changed READMEs
- Fail if README > 60 lines (keeps them dense)

### Phase 5: LLM-Ready Optimizations (Day 4)
- Add front-matter YAML at top of every MD for easy parsing
- Keep token count < 800 per file (perfect for RAG later)
- Versioned: `README.v1.md` on major changes

### Phase 6: Testing & Validation (Day 4–5)
- Run on 50 extracted elements + 20 templates
- Check: every README has specs, compliance, usage snippet
- Human spot-check: 10 random folders readable in < 30 seconds
- Round-trip: LLM prompt “summarize this wall” using only README → matches original JSON 98 %

**Total time to working v1 (full auto-generation):** 5 days  
**Milestone check:** After any extraction or new template, `README.md` appears automatically with zero manual edits. You can now `grep -r "fire_rating: 2hr"` across the entire repo and get perfect results.

This layer is the bridge to natural-language control (Item 6). Every later step reads these MD files first.

Run Phase 1–2 today on 5 templates and paste one generated README here—I’ll tweak the Jinja templates instantly.