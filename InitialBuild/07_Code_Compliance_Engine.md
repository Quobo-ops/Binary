**Code Compliance Engine (Roadmap Item 7)**  
**Goal:** Establish a centralized, version-controlled, and fully local database of building code requirements that automatically validates every element or assembly against applicable regulations. The engine ingests key provisions from major codes (International Building Code, California Building Code, Title 24, and selected local amendments), structures them for precise querying, and integrates directly with the natural language parser (Item 6), template library (Item 2), and Python API wrapper (Item 5). It returns compliance status, required modifications, and alternative compliant templates, with traceable citations to original code sections.

**Core Architecture**  
- **Storage:** SQLite database (`compliance.db`) with full-text search and relational tables for fast lookup.  
- **Data Model:** Rules linked to IFC classes, performance attributes, regions, and occupancy types.  
- **Query Interface:** Exposed through the `aecos` package as `aecos.compliance.check(element_metadata)`.  
- **Update Mechanism:** Scripted ingestion pipeline that supports annual code cycles.  
- **Output:** Structured JSON report plus Markdown summary for README.md updates.

**Database Schema (Core Tables)**  
```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY,
    code_name TEXT,           -- "CBC2025", "IBC2024", "Title24-2025"
    section TEXT,             -- "703.3.2"
    title TEXT,
    applicability TEXT,       -- JSON: {"ifc_class": ["IfcWall"], "fire_rating_min": "2hr", ...}
    requirement TEXT,         -- normalized text
    value_type TEXT,          -- "numeric", "enum", "boolean"
    citation_url TEXT,
    effective_date DATE,
    last_updated DATE
);

CREATE TABLE mappings (
    rule_id INTEGER,
    template_path TEXT,
    compliance_status TEXT  -- "compliant", "non_compliant", "partial"
);
```

**Prerequisites (45 minutes)**  
- Completion of Items 1–6.  
- `pip install sqlite-utils pdfplumber pandas sqlalchemy` (for ingestion).  
- Official PDF copies of target codes (stored in `codes/raw/`; never committed to git—use `.gitignore`).  
- `aecos` package installed in editable mode.

**Phase 1: Code Ingestion Pipeline (Day 1)**  
1. Place code PDFs in `codes/raw/`.  
2. Create `aecos/compliance/ingest.py`:  
   ```python
   import pdfplumber
   import sqlite_utils
   from pathlib import Path

   def ingest_code(pdf_path: Path, code_name: str):
       db = sqlite_utils.Database("compliance.db")
       with pdfplumber.open(pdf_path) as pdf:
           for page in pdf.pages:
               text = page.extract_text()
               # Rule extraction logic using regex or LLM-assisted chunking for tables
               # Example: extract section, title, requirements
               db["rules"].insert_many(extracted_rules)
   ```  
3. Normalize units and map to IFC attributes (thickness, fire_rating, etc.).

**Phase 2: Database Initialization and Indexing (Day 1–2)**  
- Run initial ingestion for CBC 2025, IBC 2024, and Title 24 Part 2 (Structural).  
- Add full-text search index: `db["rules"].enable_fts(["requirement", "title"])`.  
- Seed mapping table with existing library templates (cross-reference via performance tags).

**Phase 3: Query and Validation Engine (Day 2)**  
Implement in `aecos/compliance/engine.py`:  
```python
from aecos.models.element import ElementMetadata
import sqlite_utils

class ComplianceEngine:
    def __init__(self):
        self.db = sqlite_utils.Database("compliance.db")

    def check(self, element: ElementMetadata) -> dict:
        # SQL query joining rules on applicability JSON
        results = self.db.execute("""
            SELECT * FROM rules 
            WHERE json_extract(applicability, '$.ifc_class') LIKE ?
              AND region = ?
        """, [f"%{element.ifc_class}%", element.region[0]]).fetchall()
        
        violations = []
        for rule in results:
            if not self._meets_requirement(element, rule):
                violations.append(rule)
        
        return {
            "status": "compliant" if not violations else "non_compliant",
            "violations": violations,
            "suggested_templates": self._find_alternatives(element, violations)
        }
```

**Phase 4: Integration with Existing Components (Day 3)**  
- Hook into parser (Item 6): after structured output, run `engine.check()` and append compliance tags.  
- Hook into library creation: `create_element()` calls validation before saving.  
- Auto-update README.md and COMPLIANCE.md with results via Markdown layer (Item 3).

**Phase 5: Auto-Update and Regional Support (Day 3–4)**  
- Script `update_codes.py` that checks official ICC/California websites for new PDFs (or manual upload).  
- Version rules by effective date; support multiple jurisdictions simultaneously.  
- Diff tool to highlight changes between code editions.

**Phase 6: User Interface and Reporting (Day 4)**  
- CLI: `aecos compliance check "150mm concrete wall fire 2hr CA"`  
- Detailed report export (PDF/Markdown) suitable for submittals.  
- Dashboard option (optional Streamlit) for library-wide compliance overview.

**Phase 7: Testing, Accuracy, and Maintenance (Day 5)**  
- Test suite: 150 manually verified elements against published code examples.  
- Accuracy target: ≥ 98 % on fire, structural, and energy provisions.  
- Human review workflow for ambiguous rules.  
- Git-tracked `compliance.db` (via git-lfs if >50 MB) with schema migrations.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After processing a sample element (e.g., “150 mm concrete wall, 2-hour fire rated, California”), the engine returns a complete compliance report including exact section citations, pass/fail status, and one-click links to compliant alternatives from the template library.

This engine ensures every generated or extracted element is code-compliant by design, eliminating manual verification cycles and providing auditable documentation.  

Proceed with implementation of Phases 1 and 2 on a single code section (e.g., fire-resistance tables) today. Should any challenges arise during ingestion or query design, furnish the relevant details for immediate refinement.