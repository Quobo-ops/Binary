# Phase 10: Live Project Intelligence Dashboard
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 11 (Visualization), 19 (Analytics Dashboard); Phases 1–9 (all prior data sources)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Aggregates real-time element status, risk indicators, and productivity metrics into a unified, role-based dashboard drawing exclusively from local Git history and audit logs. No external analytics service, no cloud database — everything computed from the files already in the repository.

## Goal

Provide every project stakeholder with a single-page, real-time view of project health that updates automatically from the Git-stored digital thread. The dashboard answers the three questions every stakeholder asks: "Are we on schedule?", "Are we on budget?", and "Are there any problems I need to know about?"

## Core Capabilities

### 1. Real-Time Element Status Aggregation

Consolidates status from all Element folders into a project-wide view:

```markdown
## Project XYZ — Status Dashboard
**As of:** 2026-03-15 14:32 CST | **Updated:** Every git commit

### Element Status Summary
| Status | Count | Percentage | Trend |
|--------|-------|------------|-------|
| 🟢 Installed & Verified | 87 | 35.2% | ↑ +12 this week |
| 🟡 Deviation Under Review | 8 | 3.2% | ↓ -3 this week |
| 🔴 Non-Compliant / Blocked | 2 | 0.8% | → unchanged |
| 🔵 Substitution Pending | 5 | 2.0% | ↑ +2 this week |
| ⚪ Not Yet Installed | 145 | 58.7% | ↓ -11 this week |
| **Total Elements** | **247** | **100%** | |
```

### 2. Risk Indicators

Automated risk scoring based on project data:

```markdown
### Active Risk Indicators

| Risk | Severity | Trigger | Recommended Action |
|------|----------|---------|-------------------|
| Schedule Slippage | 🟡 Medium | SPI = 0.94 (below 1.0) | Review critical path activities |
| Cost Overrun | 🟡 Medium | CPI = 0.96 (trending down) | Audit change orders this month |
| Approval Bottleneck | 🔴 High | 3 approvals past 72hr timeout | Escalate to project manager |
| Resource Conflict | 🟡 Medium | Carpenter overallocation Week 14 | Delay non-critical interior work |
| Compliance Gap | 🟢 Low | 0 non-compliant elements | Continue monitoring |
```

### 3. Role-Based Views

Each stakeholder sees the information most relevant to their role:

**Designer View:**
- Substitution proposals awaiting review
- Deviation reports requiring sign-off
- Compliance status across all elements
- Design intent vs. as-built drift analysis

**Contractor View:**
- Pending installations with priority ranking
- Resource allocation and crew schedules
- Outstanding change orders and their status
- Material procurement and delivery tracking

**Owner View:**
- Budget vs. actual cost (high-level)
- Schedule milestone completion
- Quality metrics and inspection results
- Pending decisions requiring owner authorization

### 4. Productivity Metrics

Computed from Git commit history and element data:

```markdown
### Productivity Dashboard — This Week

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Elements installed | 12 | 15 | 🟡 80% |
| Substitutions processed | 5 | — | — |
| Change orders closed | 3 | — | — |
| Avg. approval cycle time | 18 hrs | <48 hrs | 🟢 |
| Field logs recorded | 28 | — | — |
| Compliance pass rate | 100% | 100% | 🟢 |
```

### 5. Trend Analysis and Forecasting

Historical trend lines computed from Git history:

- **S-curve** — Planned vs. actual progress over time
- **Burn-down** — Remaining elements to install
- **Cost trend** — Cumulative actual vs. budget
- **Velocity** — Elements completed per week (rolling average)
- **Forecast** — Projected completion date based on current velocity

### 6. Self-Contained HTML Dashboard

Generated as a single HTML file (consistent with Phase 4 approach):

```
project_XYZ/
├── DASHBOARD.html              # Self-contained, browser-viewable
├── dashboard_data/
│   ├── status.json             # Current status snapshot
│   ├── risks.json              # Active risk indicators
│   ├── metrics.json            # Productivity metrics
│   ├── trends.json             # Historical trend data
│   └── last_updated.json       # Timestamp and commit hash
```

- **Auto-refresh** — Regenerated on every Git commit (via hook)
- **Responsive** — Desktop and mobile layouts
- **Print-friendly** — Styled for PDF export (weekly reports)
- **No server** — Opens in any browser from local filesystem

## Architecture

### Module Structure
```
aecos/dashboard/
├── __init__.py
├── aggregator.py            # Collect data from all Element folders
├── risk_engine.py           # Risk scoring and indicator generation
├── metrics_calculator.py    # Productivity and performance metrics
├── trend_analyzer.py        # Historical trend and forecasting
├── role_filter.py           # Role-based view generation
├── html_generator.py        # Self-contained HTML dashboard builder
└── templates/
    ├── dashboard.html.j2    # Main dashboard template
    ├── risk_panel.html.j2   # Risk indicator component
    ├── metrics_panel.html.j2 # Metrics component
    ├── charts.js            # Embedded chart library (lightweight)
    └── print_styles.css     # Print-friendly stylesheet
```

### AecOS Facade Integration
```python
# Generate dashboard
os.generate_dashboard(project_id="XYZ")

# Role-specific view
os.generate_dashboard(project_id="XYZ", role="owner")

# Get specific metrics
os.project_status(project_id="XYZ")
os.project_risks(project_id="XYZ")
os.project_metrics(project_id="XYZ", period="this_week")

# Trend data
os.project_trends(project_id="XYZ", metric="velocity", periods=12)
```

### Data Sources (All Local)

| Data Source | Location | Metrics Derived |
|-------------|----------|----------------|
| FIELD_STATUS.md per element | Element folders | Installation progress |
| cost.json per element | Element folders | Budget vs. actual |
| SCHEDULE.md per element | Element folders | Schedule performance |
| Substitution proposals | Element/substitutions/ | Procurement activity |
| Change orders | Element/change_orders/ | CO volume and value |
| Approval records | Element/approvals/ | Approval cycle time |
| Git commit history | .git/log | Velocity, trends |
| Audit logs | Audit SQLite | Compliance, security |

## Deliverables

- [ ] `aecos/dashboard/` module with full dashboard pipeline
- [ ] Status aggregator scanning all Element folders
- [ ] Risk scoring engine with configurable thresholds
- [ ] Productivity metrics calculator
- [ ] Trend analyzer with forecasting
- [ ] Role-based view filters (designer, contractor, owner)
- [ ] Self-contained HTML dashboard generator
- [ ] Embedded lightweight chart library (no CDN)
- [ ] Print-friendly CSS for weekly report export
- [ ] Git hook for auto-regeneration on commit
- [ ] CLI command: `aecos dashboard generate --project <id>`
- [ ] CLI command: `aecos dashboard --role <role>`
- [ ] CLI command: `aecos dashboard risks --project <id>`

## Testing Strategy

```bash
# Unit tests for aggregation and risk scoring
pytest tests/test_dashboard.py

# Integration: Multi-element project → Full dashboard
pytest tests/integration/test_dashboard_pipeline.py

# HTML output validation
pytest tests/test_dashboard_html.py

# Performance: Dashboard generation time for 500-element project
pytest tests/benchmark/test_dashboard_performance.py
```

## Bible Compliance Checklist

- [x] Local-first: All metrics computed from local Git data
- [x] Git SoT: Dashboard data derived exclusively from Git history
- [x] Pure-file: HTML dashboard, JSON data files — no server
- [x] Cryptographic audit: Dashboard reflects verified audit data
- [x] Revit compatible: Element status linked to IFC identifiers
- [x] Legal/financial first: Metrics use verified cost and compliance data

---

**Dependency Chain:** Items 11, 19 + Phases 1–9 → This Module
**Next Phase:** Phase 11 (Post-Occupancy Facility Management Module)
