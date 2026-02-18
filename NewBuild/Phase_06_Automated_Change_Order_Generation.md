# Phase 6: Automated Change-Order Generation and Processing
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 7 (Compliance), 10 (Cost), 17 (Security & Audit); Phases 1 (Procurement), 2 (As-Built), 5 (NL Context)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Automates the creation of formal, signed change-order documents from field deviations, including financial and schedule impact analysis and direct export to standard industry formats. What previously took weeks of back-and-forth coordination now completes in under 48 hours with full audit trail.

## Goal

Transform field deviations (logged in Phase 2) and substitution proposals (Phase 1) into formal, industry-standard change-order documents automatically. Every change order includes cost impact, schedule impact, compliance verification, and cryptographic signatures — ready for submission without manual drafting.

## Core Capabilities

### 1. Automatic Change-Order Detection

The system monitors all field activity and triggers change-order generation when:

- **Deviation exceeds tolerance** — As-built log (Phase 2) flags out-of-tolerance condition
- **Substitution approved** — Procurement engine (Phase 1) approves a material swap with cost delta
- **Scope addition** — New work not in original contract (e.g., "Add blocking at grid B-4")
- **Scope deletion** — Work removed or simplified
- **Time impact** — Any change affecting the critical path

### 2. Financial Impact Analysis

Comprehensive cost calculation from existing engines:

```markdown
## Change Order CO-007: Wall W-EXT-01 Material Substitution

### Cost Impact Summary
| Line Item | Original | Revised | Delta |
|-----------|----------|---------|-------|
| Material (8" CMU) | $4,050.00 | — | — |
| Material (8" ICF) | — | $5,625.00 | +$1,575.00 |
| Labor (Mason crew) | $2,890.00 | — | — |
| Labor (ICF crew) | — | $2,160.00 | -$730.00 |
| Equipment | $450.00 | $320.00 | -$130.00 |
| **Net Change** | | | **+$715.00** |

### Markup & Fees
| Item | Rate | Amount |
|------|------|--------|
| Contractor OH&P | 15% | $107.25 |
| Bond premium | 1.5% | $10.73 |
| **Total Change Order** | | **$832.98** |
```

### 3. Schedule Impact Analysis

Extends the existing Cost & Schedule Hooks (Item 10) with predecessor/successor logic:

```markdown
### Schedule Impact
| Activity | Original Duration | Revised Duration | Delta |
|----------|------------------|-----------------|-------|
| Wall framing | 5 days | — (removed) | -5 days |
| ICF form setup | — | 3 days | +3 days |
| ICF pour & cure | — | 4 days | +4 days |
| **Net Schedule Impact** | | | **+2 days** |

**Critical Path Impact:** Yes — extends substantial completion by 2 days
**Recommended Mitigation:** Overlap ICF form setup with adjacent wall work
```

### 4. Document Generation

Produces industry-standard change-order documents:

| Format | Use Case | Standard |
|--------|----------|----------|
| AIA G701 | Standard change order form | AIA Contract Documents |
| AIA G709 | Proposal request | AIA Contract Documents |
| Markdown + PDF | Internal review and Git storage | AEC OS native |
| CSV export | Import to Procore, Sage, QuickBooks | Universal |
| JSON | Machine-readable for downstream systems | AEC OS native |

### 5. Approval Workflow Integration

Connects to the RBAC system (Item 17) and prepares for Phase 8 (Cross-Party Approval):

```
Change Order Lifecycle:
  Draft → Pending Review → Designer Approved → Contractor Accepted → Owner Authorized → Executed
```

Each state transition is a signed Git commit with full audit trail.

## Architecture

### Module Structure
```
aecos/change_orders/
├── __init__.py
├── detector.py              # Automatic CO trigger detection
├── financial_analyzer.py    # Cost impact calculation
├── schedule_analyzer.py     # Schedule impact with CPM logic
├── document_generator.py    # Multi-format document production
├── markup_calculator.py     # OH&P, bond, insurance calculations
├── workflow.py              # State machine for CO lifecycle
└── templates/
    ├── aia_g701.md.j2       # AIA G701 change order template
    ├── aia_g709.md.j2       # AIA G709 proposal request template
    ├── change_order.md.j2   # Internal markdown template
    ├── cost_summary.md.j2   # Detailed cost breakdown
    └── schedule_impact.md.j2 # Schedule analysis template
```

### AecOS Facade Integration
```python
# Generate change order from deviation
os.generate_change_order(
    element_id="W-EXT-01",
    deviation_id="AB-001",
    markup_rate=0.15,
    include_schedule=True
)

# Generate from substitution
os.change_order_from_substitution(
    element_id="W-EXT-01",
    substitution_id="SUB-001"
)

# Export to industry format
os.export_change_order(co_id="CO-007", format="aia_g701")

# Advance workflow state
os.approve_change_order(co_id="CO-007", role="designer")
```

### Data Flow
```
Field Deviation (Phase 2) OR Substitution (Phase 1)
    ↓
Change Order Detector → Triggers CO generation
    ↓
Financial Analyzer (Item 10 + markup tables)
    ↓
Schedule Analyzer (Item 10 + CPM logic)
    ↓
Document Generator → MD + PDF + CSV + JSON
    ↓
Workflow Engine → State: Draft
    ↓
AuditLogger (Item 17) → Signed Git Commit
```

### Element Folder Output
```
Elements/W-EXT-01/
├── ... (existing files)
├── change_orders/
│   ├── CO-007_draft.md          # Human-readable change order
│   ├── CO-007_cost.json         # Machine-readable cost breakdown
│   ├── CO-007_schedule.json     # Schedule impact data
│   ├── CO-007_aia_g701.md       # AIA standard format
│   ├── CO-007_workflow.json     # Current state + history
│   └── CO-007_audit.json        # Signed audit entries
```

## Quantified Impact

| Impact Area | Projected Benefit | Mechanism |
|-------------|-------------------|-----------|
| Change-Order Cycle Time | Weeks → <48 hours | Auto-generated, pre-analyzed packages |
| Administrative Labor | 70–85% reduction | Eliminates manual document preparation |
| Dispute Risk | Significantly reduced | Every CO backed by signed audit trail |
| Cost Accuracy | ±3% vs. industry ±15% | Direct integration with Cost Engine |
| Cash Flow | Faster payment cycles | Rapid CO processing and approval |

## Deliverables

- [ ] `aecos/change_orders/` module with full CO pipeline
- [ ] Automatic CO trigger detection from deviations and substitutions
- [ ] Financial impact analyzer with markup/OH&P calculations
- [ ] Schedule impact analyzer with critical-path awareness
- [ ] AIA G701 and G709 template renderers
- [ ] Multi-format export (Markdown, PDF, CSV, JSON)
- [ ] CO lifecycle workflow engine with state tracking
- [ ] CLI command: `aecos change-order generate <element-id> <deviation-id>`
- [ ] CLI command: `aecos change-order approve <co-id> --role <role>`
- [ ] CLI command: `aecos change-order export <co-id> --format aia_g701`

## Testing Strategy

```bash
# Unit tests for financial and schedule analysis
pytest tests/test_change_orders.py

# Integration: Deviation → CO → Approval workflow
pytest tests/integration/test_change_order_pipeline.py

# Format validation: AIA document compliance
pytest tests/test_change_order_formats.py
```

## Bible Compliance Checklist

- [x] Local-first: All analysis and document generation runs locally
- [x] Git SoT: CO documents committed to Element folder
- [x] Pure-file: Markdown, JSON, CSV — no external database
- [x] Cryptographic audit: Every CO state transition signed
- [x] Revit compatible: CO data references IFC element identifiers
- [x] Legal/financial first: AIA-standard formats, signed documents

---

**Dependency Chain:** Phases 1, 2, 5 + Items 7, 10, 17 → This Module
**Next Phase:** Phase 7 (4D/5D Construction Sequencing Layer)
