# Phase 1: Contractor Procurement and Substitution Engine
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 2 (Template Library), 6 (NLParser), 7 (Compliance Engine), 10 (Cost & Schedule Hooks), 17 (Security & Audit)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Introduces natural-language material and product substitution workflows for contractors, with automatic compliance validation, cost delta computation, lead-time assessment, and submittal package generation — all executed within existing Element folders. This is the first contractor-facing capability and is designed to deliver immediate, tangible value on $50k design / $500k build projects.

## Goal

Enable contractors to propose and validate material substitutions in natural language with automatic compliance, cost, and lead-time checks. A foreman or superintendent can say "Replace wall W-EXT-01 with 8-inch CMU block from ABC Masonry Baton Rouge plant" and receive instant, validated feedback — no training required.

## Core Capabilities

### 1. Natural-Language Substitution Interface

Reuses the unified NLParser (Item 6) with a contractor-specific context vector loaded from the Element folder:

- **Material catalogs** — Regional supplier SKUs, product lines, equivalency tables
- **Crew rates** — Louisiana-specific labor rates by trade, updated quarterly
- **Site constraints** — Project-specific restrictions (access, crane reach, staging)
- **Role-based context** — Contractor vs. designer intent differentiation

**Example Commands:**
```
"Replace wall W-EXT-01 with 8-inch CMU block from ABC Masonry Baton Rouge plant"
"Substitute specified Andersen windows with Pella 250 series, same performance"
"Use local cypress siding instead of fiber cement on south elevation"
"Check if 3/4" plywood can replace 23/32" OSB for roof sheathing"
```

### 2. Automatic Compliance Validation

Every substitution proposal is instantly validated against:

- **Performance requirements** — Fire rating, structural capacity, thermal R-value, acoustic STC
- **Code references** — IBC, Louisiana amendments, project-specific specifications
- **Specification conformance** — Section-by-section spec compliance check
- **Material compatibility** — Substrate, fastener, finish compatibility matrices

**Output:** Pass/Fail with detailed justification and code citations.

### 3. Cost Delta Computation

Leverages the existing Cost Engine (Item 10) to produce:

- **Material cost delta** — Unit price difference × quantity
- **Labor cost impact** — Installation complexity adjustment (e.g., CMU requires masons vs. framers)
- **Total installed cost comparison** — Side-by-side original vs. proposed
- **Lead-time impact** — Supplier delivery schedule vs. project timeline

### 4. Submittal Package Generation

Auto-generates a complete submittal package for each approved substitution:

- **Substitution request form** — Markdown + signed PDF
- **Spec sheet placeholder** — Links to manufacturer cut sheets
- **Cost comparison table** — Itemized delta with source citations
- **Compliance certification** — Signed validation from Compliance Engine
- **Lead-time analysis** — Delivery timeline vs. construction schedule

## Architecture

### Module Structure
```
aecos/procurement/
├── __init__.py
├── substitution.py          # Core substitution logic
├── validator.py             # Compliance validation for substitutions
├── cost_delta.py            # Cost comparison engine
├── submittal_generator.py   # Submittal package builder
├── catalog_manager.py       # Local supplier catalog CRUD
└── catalogs/
    ├── louisiana_suppliers.csv
    ├── material_equivalency.json
    └── crew_rates_la_2026.json
```

### AecOS Facade Integration
```python
# New facade methods
os.contract_substitute(element_id="W-EXT-01", spec="8-inch CMU block from ABC Masonry")
os.validate_substitution(element_id="W-EXT-01", proposal_id="SUB-001")
os.generate_submittal(element_id="W-EXT-01", proposal_id="SUB-001")
os.list_alternatives(element_id="W-EXT-01", criteria={"min_fire_rating": "2H"})
```

### Data Flow
```
Contractor NL Input
    ↓
NLParser (Item 6) + Contractor Context Vector
    ↓
Substitution Proposal (JSON in Element folder)
    ↓
Compliance Engine (Item 7) → Pass/Fail + Citations
    ↓
Cost Engine (Item 10) → Delta Calculation
    ↓
Submittal Generator → Package (MD + PDF)
    ↓
AuditLogger (Item 17) → Signed Git Commit
```

### Element Folder Output
```
Elements/W-EXT-01/
├── ... (existing files)
├── substitutions/
│   ├── SUB-001_proposal.json
│   ├── SUB-001_compliance.md
│   ├── SUB-001_cost_delta.json
│   ├── SUB-001_submittal.md
│   └── SUB-001_audit.json
```

## Regional Catalog Management

Local CSV catalogs ship with the system and are updated via `git pull` from the firm's private library:

| Catalog | Content | Update Frequency |
|---------|---------|------------------|
| `louisiana_suppliers.csv` | Supplier name, SKU, unit cost, lead time, location | Quarterly |
| `material_equivalency.json` | Spec-to-product mapping with performance data | Per project |
| `crew_rates_la_2026.json` | Trade rates by parish, union/non-union | Annually |

## Quantified Impact

| Impact Area | Projected Benefit | Mechanism |
|-------------|-------------------|-----------|
| RFI & Coordination Labor | 35–55% reduction | Pre-validated substitutions never become RFIs |
| Material & Procurement Cost | 10–18% lower effective cost | Instant supplier-SKU + regional pricing checks |
| Submittal Cycle Time | Days → minutes | Auto-generated, code-checked packages |
| Contractor Bid Contingency | 6–12% reduction | Transparent, auditable substitution thread |

## Deliverables

- [ ] `aecos/procurement/` module with full substitution pipeline
- [ ] Extended NLParser context vector for contractor vocabulary
- [ ] Submittal package generator (Markdown + PDF)
- [ ] Local catalog management system with CSV/JSON import
- [ ] Louisiana regional supplier catalog (initial dataset)
- [ ] Crew rate tables for Baton Rouge metro area
- [ ] Integration tests against existing Compliance and Cost engines
- [ ] CLI command: `aecos substitute <element-id> "<description>"`

## Testing Strategy

```bash
# Unit tests for substitution validation
pytest tests/test_procurement.py

# Integration: NLParser → Substitution → Compliance → Cost
pytest tests/integration/test_substitution_pipeline.py

# Benchmark: 50 common substitutions validated against manual review
pytest tests/benchmark/test_substitution_accuracy.py
```

## Bible Compliance Checklist

- [x] Local-first: All validation and catalog lookup runs locally
- [x] Git SoT: Substitution proposals committed to Element folder
- [x] Pure-file: JSON proposals, Markdown submittals, CSV catalogs
- [x] Cryptographic audit: Every substitution signed via AuditLogger
- [x] Revit compatible: Updated IFC re-exportable for Revit re-link
- [x] Legal/financial first: Compliance check mandatory before cost calc

---

**Dependency Chain:** NLParser (Item 6) → Compliance Engine (Item 7) → Cost Engine (Item 10) → This Module
**Next Phase:** Phase 2 (Live As-Built Logging and Verification)
