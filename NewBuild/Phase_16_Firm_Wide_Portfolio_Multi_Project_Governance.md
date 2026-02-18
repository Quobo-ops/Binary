# Phase 16: Firm-Wide Portfolio and Multi-Project Governance
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 2 (Template Library), 4 (VCS), 12 (Multi-User Sync), 16 (Collaboration), 17 (Security & Audit); Phases 10 (Dashboard), 12 (Fine-Tuning)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Enables centralized template governance and cross-project learning while maintaining complete data isolation and local-first operation. A firm managing multiple concurrent projects needs portfolio-level visibility, standardized templates, and shared best practices — all without breaking the fundamental principle that each project's data remains self-contained and locally controlled.

## Goal

Provide firm principals and BIM managers with a single pane of glass across all active projects while preserving the per-project isolation, local-first execution, and Git-based architecture that define AEC OS. Knowledge flows up (aggregated metrics) and down (standardized templates and policies), but project data never leaks sideways.

## Core Capabilities

### 1. Portfolio Dashboard

Aggregate view across all firm projects:

```markdown
## Firm Portfolio Dashboard — Monson Architecture
**Active Projects:** 8 | **Total Elements:** 1,847 | **As of:** 2026-03-15

### Project Status Summary
| Project | Phase | Elements | Budget | Schedule | Risk |
|---------|-------|----------|--------|----------|------|
| Riverside Office | Construction | 247 | 🟢 $487k (on budget) | 🟡 SPI 0.94 | Medium |
| Downtown Lofts | Design | 185 | 🟢 $320k (est.) | 🟢 On track | Low |
| Parish Library | Closeout | 312 | 🟢 $615k (under) | 🟢 Complete | Low |
| Bayou Mixed-Use | Permitting | 420 | 🟡 $1.2M (review) | 🟢 On track | Medium |
| Oak Street Reno | Construction | 128 | 🔴 $195k (over 8%) | 🔴 SPI 0.82 | High |
| ...3 more | | | | | |

### Firm-Wide Metrics (Rolling 90 Days)
| Metric | Value | Trend |
|--------|-------|-------|
| Avg. compliance pass rate | 99.8% | → Stable |
| Template reuse rate | 74% | ↑ Improving |
| Avg. change order cycle time | 22 hrs | ↓ Improving |
| Total cost managed | $3.2M | |
| Active field users | 34 | |
```

### 2. Template Governance

Centralized management of firm-standard templates:

```
Firm Template Library (Central Repo)
    ├── Standards/
    │   ├── Walls/          # Firm-standard wall assemblies
    │   ├── Doors/          # Standard door types and hardware
    │   ├── Windows/        # Approved window specifications
    │   └── MEP/            # Standard mechanical/electrical
    ├── Regional/
    │   ├── Louisiana/      # State-specific requirements
    │   └── National/       # National code baselines
    └── Project-Types/
        ├── Office/         # Office building standards
        ├── Residential/    # Multi-family standards
        └── Institutional/  # Library/civic standards

Governance Workflow:
  1. Designer creates/modifies template in project
  2. Submits for firm-library inclusion
  3. BIM Manager reviews for standards compliance
  4. Approved → Published to firm template repo
  5. Projects pull updates via git fetch from firm repo
```

### 3. Policy Enforcement

Firm-wide policies that apply across all projects:

```json
{
  "firm_policies": {
    "compliance": {
      "minimum_code_set": ["IBC_2024", "Louisiana_amendments"],
      "fire_rating_verification": "mandatory",
      "accessibility_check": "mandatory"
    },
    "cost": {
      "change_order_threshold_owner_approval": 5000,
      "contingency_minimum_pct": 10,
      "markup_standard_pct": 15
    },
    "quality": {
      "peer_review_required": true,
      "minimum_template_reuse_pct": 60,
      "sustainability_check": "recommended"
    },
    "security": {
      "key_rotation_days": 90,
      "audit_retention_years": 10,
      "mfa_required": true
    }
  }
}
```

### 4. Cross-Project Learning (Anonymized)

Pattern recognition across the portfolio:

```markdown
## Cross-Project Insights — Q1 2026

### Cost Patterns
- Baton Rouge concrete prices 8% below national; recommend local sourcing
- ICF walls showing 12% cost savings vs. CMU across 3 projects
- HVAC installation labor consistently 15% above estimates → adjust base rates

### Schedule Patterns
- Foundation work averaging 1.3x estimated duration (soil conditions)
- Interior finish trades available earlier than planned → opportunity
- Permit review times: Parish avg 28 days, City avg 42 days

### Quality Patterns
- Zero compliance failures on elements using firm templates
- 3 deviations traced to non-standard substitutions → tighten review
- Field logging adoption: 92% among trained foremen

### Recommendations
1. Update foundation duration estimates +30% for Louisiana clay soil
2. Add ICF as preferred alternative to CMU in firm standards
3. Adjust HVAC labor rates in crew rate tables
```

### 5. Data Isolation Enforcement

Strict boundaries between project data:

```python
class ProjectIsolation:
    """Ensures project data never leaks between projects."""

    def aggregate_metrics(self, projects: list) -> PortfolioMetrics:
        """Collect only approved metrics from each project."""
        metrics = []
        for project in projects:
            # Only read pre-approved metric files
            metrics.append(self._read_metrics_only(project))
            # NEVER read element data, audit logs, or financial details
        return PortfolioMetrics.aggregate(metrics)

    def share_template(self, source_project: str, template_id: str):
        """Share template via firm central repo — never direct project-to-project."""
        # Copy template to firm repo staging area
        # Strip project-specific data
        # Require BIM Manager approval
        # Publish to firm template library
        pass
```

### 6. Role-Based Portfolio Access

| Role | Access Level | Can See | Cannot See |
|------|-------------|---------|------------|
| Principal | Full portfolio | All project summaries, firm metrics | Individual audit entries |
| BIM Manager | Template + standards | Templates, compliance rates, quality | Financial details |
| Project Manager | Assigned projects | Full detail on own projects | Other project details |
| Designer | Assigned projects | Design data, templates | Financial, other projects |
| Contractor | Assigned project only | Own project field data | Everything else |

## Architecture

### Module Structure
```
aecos/portfolio/
├── __init__.py
├── aggregator.py            # Cross-project metric aggregation
├── template_governor.py     # Template governance workflow
├── policy_enforcer.py       # Firm-wide policy enforcement
├── isolation_guard.py       # Data isolation enforcement
├── cross_project_learner.py # Anonymized pattern recognition
├── portfolio_dashboard.py   # Multi-project dashboard generator
└── templates/
    ├── portfolio_dashboard.html.j2
    ├── template_review.md.j2
    ├── policy_report.md.j2
    └── cross_project_insights.md.j2
```

### AecOS Facade Integration
```python
# Portfolio overview
os.portfolio_dashboard()
os.portfolio_metrics(period="last_90_days")
os.portfolio_risks()

# Template governance
os.submit_template(template_id="W-EXT-ICF-01", to="firm_library")
os.review_template(submission_id="TS-001", decision="approve")
os.pull_firm_templates(project_id="XYZ")

# Policy management
os.check_policy_compliance(project_id="XYZ")
os.update_firm_policy(policy_key="cost.markup_standard_pct", value=15)

# Cross-project learning
os.cross_project_insights(period="Q1_2026")
```

## Deliverables

- [ ] `aecos/portfolio/` module with full governance pipeline
- [ ] Portfolio dashboard aggregating all active projects
- [ ] Template governance workflow (submit → review → publish)
- [ ] Firm-wide policy definition and enforcement engine
- [ ] Data isolation guard ensuring project separation
- [ ] Cross-project learning engine (anonymized patterns)
- [ ] Role-based portfolio access controls
- [ ] Firm template repository structure and sync mechanism
- [ ] CLI command: `aecos portfolio dashboard`
- [ ] CLI command: `aecos portfolio metrics`
- [ ] CLI command: `aecos template submit <id> --to firm-library`
- [ ] CLI command: `aecos policy check --project <id>`

## Testing Strategy

```bash
# Unit tests for aggregation and isolation
pytest tests/test_portfolio.py

# Integration: Multi-project → Portfolio dashboard
pytest tests/integration/test_portfolio_pipeline.py

# Isolation tests: Verify no data leakage
pytest tests/test_data_isolation.py

# Template governance workflow
pytest tests/test_template_governance.py
```

## Bible Compliance Checklist

- [x] Local-first: Portfolio computed from local project data, no central server
- [x] Git SoT: Firm templates in Git repo, project data in project repos
- [x] Pure-file: JSON policies, Markdown reports, HTML dashboard
- [x] Cryptographic audit: Template governance decisions signed
- [x] Revit compatible: Firm templates are standard Element folders
- [x] Legal/financial first: Data isolation protects client confidentiality

---

**Dependency Chain:** Items 2, 4, 12, 16, 17 + Phases 10, 12 → This Module
**Next Phase:** Phase 17 (Secure, Optional Ecosystem Integrations)
