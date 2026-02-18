# Phase 11: Post-Occupancy Facility Management Module
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 1–19 (full v1.0 core); Phases 1–10 (full construction thread); Phase 3 (Handover Package)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Adds asset-tracking, preventive-maintenance scheduling, warranty management, and performance-monitoring capabilities that continue to operate on the same Element folders after handover. The digital thread does not end at substantial completion — it extends into decades of facility operation, using the identical architecture that served design and construction.

## Goal

Transform the handover package (Phase 3) from a static archive into a living facility management system. Building owners and facility managers use the same Element folders, the same Git repository, and the same CLI/mobile interface to manage assets, schedule maintenance, track warranties, and monitor building performance.

## Core Capabilities

### 1. Asset Registry and Tracking

Every Element becomes a tracked facility asset:

```json
{
  "asset_id": "W-EXT-01",
  "asset_class": "building_envelope",
  "category": "exterior_wall",
  "location": {
    "building": "Main",
    "floor": 1,
    "zone": "South Elevation",
    "grid": "A1-A5"
  },
  "installed_date": "2026-03-05",
  "warranty_expiry": "2036-03-05",
  "expected_lifespan_years": 50,
  "replacement_cost_2026": 5625.00,
  "condition_score": 95,
  "last_inspection": "2026-04-01",
  "next_maintenance": "2027-03-05",
  "qr_code": "elements/W-EXT-01/qr_tag.svg"
}
```

### 2. Preventive Maintenance Scheduling

Automated maintenance calendar generated from manufacturer specs and industry standards:

```markdown
## Maintenance Schedule: W-EXT-01 (ICF Exterior Wall)

| Task | Frequency | Next Due | Assigned | Est. Cost |
|------|-----------|----------|----------|-----------|
| Visual inspection | Annual | 2027-03-05 | FM Team | $50 |
| Sealant inspection | Annual | 2027-03-05 | FM Team | $50 |
| Sealant replacement | 5 years | 2031-03-05 | Contractor | $1,200 |
| Coating/paint refresh | 7 years | 2033-03-05 | Contractor | $3,500 |
| Structural assessment | 10 years | 2036-03-05 | Engineer | $2,500 |

### Upcoming Maintenance (Next 90 Days)
| Element | Task | Due Date | Priority |
|---------|------|----------|----------|
| HVAC-01 | Filter replacement | 2026-04-15 | 🟡 Medium |
| D-101 | Hardware lubrication | 2026-04-20 | 🟢 Low |
| ROOF-01 | Visual inspection | 2026-05-01 | 🟡 Medium |
```

### 3. Warranty Management

Centralized warranty tracking with expiration alerting:

```markdown
## Warranty Dashboard

### Active Warranties
| Element | Manufacturer | Warranty Type | Start | Expiry | Remaining |
|---------|-------------|---------------|-------|--------|-----------|
| W-EXT-01 | ABC Building | Material 10yr | 2026-03 | 2036-03 | 9 yr 11 mo |
| D-101 | Allegion | Hardware 5yr | 2026-03 | 2031-03 | 4 yr 11 mo |
| HVAC-01 | Trane | Parts 5yr / Comp 10yr | 2026-04 | 2031-04 | 5 yr 0 mo |
| ROOF-01 | GAF | System 20yr | 2026-04 | 2046-04 | 19 yr 11 mo |

### Warranty Alerts
| Alert | Element | Action Required | Deadline |
|-------|---------|----------------|----------|
| 🟡 Expiring in 6 months | ELEC-12 | Renew or replace | 2026-09-15 |
| 🔴 Claim required | PLMB-05 | Document defect before warranty expires | 2026-06-01 |
```

### 4. Performance Monitoring

Track building performance metrics over time:

- **Energy consumption** — Monthly utility data logging per zone
- **Comfort metrics** — Temperature, humidity, air quality complaints
- **Water usage** — Metered consumption vs. design targets
- **Maintenance cost tracking** — Actual vs. budgeted per asset
- **Condition scoring** — Degradation tracking over time

```markdown
## Performance Report — Q1 2027

| Metric | Design Target | Actual | Variance | Status |
|--------|--------------|--------|----------|--------|
| Energy (kBTU/sf/yr) | 45.0 | 42.3 | -6.0% | 🟢 Better |
| Water (gal/sf/yr) | 15.0 | 16.2 | +8.0% | 🟡 Investigate |
| Maint. Cost ($/sf/yr) | 2.50 | 2.15 | -14.0% | 🟢 Better |
| Comfort Complaints | <5/mo | 3 | — | 🟢 |
```

### 5. Work Order Management

Simple, Git-backed work order system for facility teams:

```
Facility Manager: "HVAC unit on second floor making grinding noise"
    ↓
NLParser → Work order WO-042 created
    ↓
Asset lookup: HVAC-02, 2nd floor, Trane RTU
    ↓
Warranty check: Active (parts covered until 2031)
    ↓
Maintenance history: Last serviced 2026-10-15
    ↓
Priority: 🟡 Medium (operational but degraded)
    ↓
Assignment: FM Team → scheduled for next business day
```

### 6. Lifecycle Cost Tracking

Cumulative total cost of ownership per asset:

```markdown
## Lifecycle Cost: HVAC-01

| Category | Year 1 | Year 2 | Year 3 | Cumulative |
|----------|--------|--------|--------|------------|
| Installation | $18,500 | — | — | $18,500 |
| Energy | $2,400 | $2,520 | $2,650 | $7,570 |
| Maintenance | $150 | $350 | $500 | $1,000 |
| Repairs | $0 | $0 | $800 | $800 |
| **Total** | **$21,050** | **$2,870** | **$3,950** | **$27,870** |

**Projected 20-Year TCO:** $85,200
**Design Estimate TCO:** $82,000
**Variance:** +3.9%
```

## Architecture

### Module Structure
```
aecos/facility/
├── __init__.py
├── asset_registry.py        # Asset tracking and registry
├── maintenance_scheduler.py # Preventive maintenance engine
├── warranty_manager.py      # Warranty tracking and alerting
├── performance_monitor.py   # Building performance metrics
├── work_order_manager.py    # Work order lifecycle
├── lifecycle_cost.py        # TCO tracking and projection
├── condition_scorer.py      # Asset condition assessment
└── templates/
    ├── maintenance_schedule.md.j2
    ├── warranty_dashboard.md.j2
    ├── performance_report.md.j2
    ├── work_order.md.j2
    └── lifecycle_cost.md.j2
```

### AecOS Facade Integration
```python
# Asset management
os.register_asset(element_id="HVAC-01", installed_date="2026-04-01")
os.asset_status(element_id="HVAC-01")
os.asset_condition_update(element_id="HVAC-01", score=92, notes="Minor wear")

# Maintenance
os.maintenance_schedule(project_id="XYZ", next_days=90)
os.log_maintenance(element_id="HVAC-01", task="filter_replacement", cost=85.00)

# Warranties
os.warranty_status(element_id="HVAC-01")
os.warranty_alerts(project_id="XYZ", within_months=6)

# Work orders
os.create_work_order(element_id="HVAC-02", description="Grinding noise")
os.update_work_order(wo_id="WO-042", status="completed", cost=350.00)

# Performance
os.log_performance(project_id="XYZ", metric="energy", value=42.3, period="2027-Q1")
os.performance_report(project_id="XYZ", period="2027-Q1")
```

### Element Folder Extension (Post-Handover)
```
Elements/HVAC-01/
├── ... (existing design + construction files)
├── facility/
│   ├── asset_record.json        # Asset registry entry
│   ├── MAINTENANCE_LOG.md       # Chronological maintenance record
│   ├── WARRANTY.md              # Warranty details and status
│   ├── PERFORMANCE.md           # Performance metrics over time
│   ├── work_orders/
│   │   ├── WO-042.json
│   │   └── WO-042.md
│   └── LIFECYCLE_COST.md        # Cumulative TCO tracking
```

## Deliverables

- [ ] `aecos/facility/` module with full FM capabilities
- [ ] Asset registry system built on Element folders
- [ ] Preventive maintenance scheduler with manufacturer-based intervals
- [ ] Warranty management with expiration alerting
- [ ] Performance monitoring with design-target comparison
- [ ] Work order management with NL interface
- [ ] Lifecycle cost tracker and TCO projector
- [ ] Condition scoring system for asset degradation tracking
- [ ] CLI command: `aecos facility status --project <id>`
- [ ] CLI command: `aecos facility maintenance --next <days>`
- [ ] CLI command: `aecos facility work-order create <element-id> "<description>"`
- [ ] CLI command: `aecos facility warranty-alerts --within <months>`

## Testing Strategy

```bash
# Unit tests for all facility components
pytest tests/test_facility.py

# Integration: Handover → Asset registration → Maintenance → Work orders
pytest tests/integration/test_facility_pipeline.py

# Warranty alerting tests
pytest tests/test_warranty_alerts.py

# Performance metric accuracy
pytest tests/test_performance_metrics.py
```

## Bible Compliance Checklist

- [x] Local-first: All FM operations run on local Element folders
- [x] Git SoT: Maintenance logs, work orders committed to Git
- [x] Pure-file: JSON records, Markdown reports — no FM database
- [x] Cryptographic audit: Maintenance actions signed via AuditLogger
- [x] Revit compatible: Asset IDs trace back to original IFC elements
- [x] Legal/financial first: Warranty tracking protects legal rights

---

**Dependency Chain:** Phase 3 (Handover) + Phases 1–10 → This Module
**Next Phase:** Phase 12 (Continuous Field-Driven Fine-Tuning Loop)
