# Phase 5: Contractor-Specific Natural-Language Context Engine
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 6 (NLParser), 7 (Compliance), 10 (Cost), 13 (Fine-Tuning Loop), 14 (Domain Expansion); Phases 1–4
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Extends the existing NLParser with construction-domain vocabulary, crew-rate tables, site-constraint awareness, and role-based context loading while preserving the single unified parser architecture. This is not a separate parser — it enriches the existing one with deep field knowledge so that designers and contractors share the same language pipeline.

## Goal

Make the NLParser (Item 6) natively fluent in construction vocabulary, trade slang, regional terminology, and contractor-specific workflows. A framer saying "sister the joist" and an architect saying "reinforce the floor framing member" should both produce the same validated parametric spec.

## Core Capabilities

### 1. Construction Domain Vocabulary

Extends the NLParser lexicon with field-native terminology:

| Trade Term | Formal Equivalent | IFC Mapping |
|------------|------------------|-------------|
| "sister the joist" | Add reinforcing joist alongside existing | IfcBeam (reinforcement) |
| "shoot the slab" | Place concrete slab | IfcSlab (placement) |
| "rough in" | Install concealed components before close-up | IfcBuildingElementProxy |
| "punch list" | Deficiency list for completion | QualityCheck (custom) |
| "back-charge" | Cost reallocation to responsible party | CostAdjustment |
| "daylight the pipe" | Expose buried utility | IfcPipeSegment (exposure) |
| "mud the wall" | Apply joint compound/drywall finishing | IfcCovering (finish) |
| "pick the steel" | Crane-lift steel members into position | IfcBeam/IfcColumn (install) |

### 2. Crew-Rate Tables

Locally stored, project-configurable labor rate data:

```json
{
  "region": "Baton Rouge Metro",
  "effective_date": "2026-Q1",
  "rates": {
    "carpenter_journeyman": { "hourly": 42.50, "burden": 1.45, "loaded": 61.63 },
    "electrician_journeyman": { "hourly": 48.00, "burden": 1.52, "loaded": 72.96 },
    "ironworker_journeyman": { "hourly": 52.00, "burden": 1.48, "loaded": 76.96 },
    "laborer_general": { "hourly": 28.00, "burden": 1.38, "loaded": 38.64 },
    "mason_journeyman": { "hourly": 44.00, "burden": 1.46, "loaded": 64.24 },
    "plumber_journeyman": { "hourly": 50.00, "burden": 1.50, "loaded": 75.00 },
    "operator_crane": { "hourly": 55.00, "burden": 1.52, "loaded": 83.60 }
  }
}
```

### 3. Site-Constraint Awareness

The parser understands spatial and logistical constraints:

```
"Can't get the boom truck past grid line 4 — need to hand-carry"
→ Constraint: access_restriction at grid_4, equipment=manual_carry
→ Impact: labor_multiplier=2.5x for elements beyond grid 4

"Overhead power lines on the south side — no crane within 20 feet"
→ Constraint: crane_exclusion_zone, south_side, radius=20ft
→ Impact: alternative_install_method required for south elements
```

### 4. Role-Based Context Loading

The same NLParser instance loads different context based on the authenticated role:

| Role | Context Loaded | Vocabulary Emphasis |
|------|---------------|-------------------|
| Designer | Design specs, code requirements, material properties | Formal AEC terminology |
| Contractor / Super | Crew rates, installation methods, site constraints | Trade slang, field terms |
| Owner | Cost summaries, schedule milestones, warranty data | Business terminology |
| Inspector | Code sections, inspection checklists, deficiency items | Regulatory language |

```python
class ContextLoader:
    def load_for_role(self, role: str, element_folder: Path) -> dict:
        base = self._load_element_context(element_folder)
        role_overlay = self._load_role_context(role)
        site_constraints = self._load_site_constraints(element_folder)
        return {**base, **role_overlay, "constraints": site_constraints}
```

### 5. Synonym Resolution and Disambiguation

Multi-layer resolution for ambiguous field language:

```
Input: "Add some blocking for the TV mount"
    ↓
Step 1 — Trade vocabulary: "blocking" = solid wood between studs
Step 2 — Context: TV mount = residential/commercial finish wall
Step 3 — Spec inference: 2×4 or 2×6 blocking at specified height
Step 4 — Compliance: Check wall cavity depth, fire-blocking requirements
Step 5 — Output: ParametricSpec for IfcBuildingElementProxy(blocking)
    with height, spacing, material, attachment method
```

## Architecture

### Module Structure
```
aecos/nlp/
├── ... (existing NLParser files)
├── contexts/
│   ├── __init__.py
│   ├── contractor_context.py    # Contractor-specific context loader
│   ├── designer_context.py      # Designer context (existing, refactored)
│   ├── owner_context.py         # Owner context
│   └── inspector_context.py     # Inspector context
├── vocabularies/
│   ├── construction_trades.json # Trade terminology → formal mapping
│   ├── louisiana_regional.json  # Regional terms and materials
│   ├── synonyms.json           # Multi-level synonym resolution
│   └── abbreviations.json      # Field abbreviations (o.c., typ., sim.)
├── crew_rates/
│   ├── baton_rouge_2026_q1.json
│   └── rate_loader.py
└── site_constraints/
    ├── constraint_parser.py     # Parse site constraint statements
    └── impact_calculator.py     # Calculate labor/cost impacts
```

### NLParser Extension (Unified Architecture)
```python
# The existing NLParser gains context awareness — no separate parser
class NLParser:
    def parse(self, text: str, context: dict = None) -> ParametricSpec:
        # Existing parsing pipeline
        tokens = self.tokenize(text)

        # NEW: Apply context-specific vocabulary resolution
        if context and context.get("role") == "contractor":
            tokens = self._resolve_trade_vocabulary(tokens)
            tokens = self._apply_site_constraints(tokens, context)

        # Continue existing pipeline
        intent = self.classify_intent(tokens)
        spec = self.extract_spec(tokens, intent)

        # NEW: Enrich with crew rates and cost context
        if context and "crew_rates" in context:
            spec.labor_estimate = self._estimate_labor(spec, context["crew_rates"])

        return spec
```

## Example Processing

### Contractor Input
```
INPUT: "Sister the floor joists in unit 204 — they're bouncy, use LVL"
ROLE: contractor

PROCESSING:
1. Trade vocab: "sister" → reinforce alongside, "bouncy" → excessive deflection
2. Context: unit 204 → residential floor system, existing joists
3. Material: "LVL" → Laminated Veneer Lumber
4. Compliance: Check deflection limits (L/360 live, L/240 total)
5. Cost: LVL material + carpenter labor at LA rate

OUTPUT:
{
  "intent": "modify",
  "entity_type": "IfcBeam",
  "action": "reinforce_alongside",
  "properties": {
    "material": "LVL",
    "location": "unit_204_floor",
    "reason": "excessive_deflection"
  },
  "labor_estimate": {
    "hours": 4.5,
    "trade": "carpenter_journeyman",
    "loaded_cost": 277.34
  },
  "confidence": 0.91
}
```

## Deliverables

- [ ] Construction trade vocabulary database (500+ terms)
- [ ] Louisiana regional terminology and material names
- [ ] Crew-rate table system with quarterly update mechanism
- [ ] Site-constraint parser and impact calculator
- [ ] Role-based context loader (contractor, designer, owner, inspector)
- [ ] Synonym resolution engine with disambiguation
- [ ] Integration with existing NLParser — zero breaking changes
- [ ] Field abbreviation expander (o.c., typ., sim., ea., lf., sf.)
- [ ] Updated test suite covering trade vocabulary parsing
- [ ] CLI: `aecos parse --role contractor "<field command>"`

## Testing Strategy

```bash
# Vocabulary resolution tests
pytest tests/test_nlp_contractor.py

# Cross-role equivalence tests
pytest tests/test_nlp_role_parity.py

# Regional term tests (Louisiana-specific)
pytest tests/test_nlp_regional.py
```

## Bible Compliance Checklist

- [x] Local-first: All vocabulary and context data stored locally
- [x] Git SoT: Vocabulary files and crew rates version-controlled
- [x] Pure-file: JSON vocabularies, JSON crew rates — no database
- [x] Cryptographic audit: Parse results logged via AuditLogger
- [x] Revit compatible: Output specs unchanged — same IFC pipeline
- [x] Legal/financial first: Crew rates traceable to published sources

---

**Dependency Chain:** Items 6, 7, 10, 13, 14 + Phases 1–4 → This Module
**Next Phase:** Phase 6 (Automated Change-Order Generation and Processing)
