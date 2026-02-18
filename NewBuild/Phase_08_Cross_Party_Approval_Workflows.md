# Phase 8: Cross-Party Approval and Sign-Off Workflows
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 12 (Multi-User Sync), 16 (Collaboration Layer), 17 (Security & Audit); Phases 1 (Procurement), 2 (As-Built), 6 (Change Orders)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Implements mandatory digital approval gates spanning designer, contractor, and owner roles, fully integrated with the existing RBAC and AuditLogger systems. This formalizes the multi-party decision-making that occurs on every construction project — substitutions, change orders, deviations, inspections — into a cryptographically signed, auditable workflow.

## Goal

Replace paper-based, email-driven approval processes with structured digital workflows where every approval gate is a signed Git commit. Designers, contractors, owners, and inspectors each have defined approval authorities, and no action proceeds without the required sign-offs.

## Core Capabilities

### 1. Approval Gate Definitions

Configurable approval matrices per action type:

| Action | Required Approvals | Order | Timeout |
|--------|-------------------|-------|---------|
| Material Substitution | Designer → Owner | Sequential | 72 hrs |
| Change Order (<$5k) | Designer → Contractor | Sequential | 48 hrs |
| Change Order (>$5k) | Designer → Owner → Contractor | Sequential | 120 hrs |
| As-Built Deviation (within tolerance) | Designer | Single | 48 hrs |
| As-Built Deviation (outside tolerance) | Designer → Inspector → Owner | Sequential | 168 hrs |
| Milestone Completion | Contractor → Designer → Owner | Sequential | 72 hrs |
| Final Inspection | Inspector → Designer → Owner | Sequential | 168 hrs |
| Payment Application | Contractor → Designer → Owner | Sequential | 120 hrs |

### 2. Digital Signature Workflow

Every approval is a cryptographically signed Git commit:

```json
{
  "approval": {
    "action": "substitution_approval",
    "element_id": "W-EXT-01",
    "reference": "SUB-001",
    "approver": {
      "name": "B. Monson",
      "role": "designer",
      "key_fingerprint": "A1B2C3D4..."
    },
    "decision": "approved",
    "conditions": ["ICF installer must be certified", "Submit revised shop drawings"],
    "timestamp": "2026-03-15T14:32:00-06:00",
    "signature": "SHA256:..."
  }
}
```

### 3. Escalation and Timeout Logic

Automated handling of stalled approvals:

```
Approval Timeline:
  T+0h    Request submitted → Notification sent
  T+24h   Reminder #1 (if not acted upon)
  T+48h   Reminder #2 + escalation to backup approver
  T+72h   Timeout → Auto-escalate to project manager
  T+168h  Critical timeout → Flag for executive review
```

### 4. Conditional Approvals

Approvers can attach conditions that must be satisfied:

```markdown
## Approval: SUB-001 (Wall W-EXT-01 Material Substitution)

**Decision:** APPROVED WITH CONDITIONS

**Conditions:**
1. [ ] ICF installer must hold ICC certification — verify before mobilization
2. [ ] Revised shop drawings submitted and approved
3. [ ] R-value verification test after installation

**Condition Tracking:**
- Condition 1: Pending (assigned to Contractor)
- Condition 2: Pending (assigned to Contractor)
- Condition 3: Future (triggers after installation)

**Approval is PROVISIONAL until all conditions are satisfied.**
```

### 5. Delegation and Proxy Approvals

Role-based delegation for when primary approvers are unavailable:

```python
# Delegation rules (stored in project config)
{
  "delegations": [
    {
      "from": "b.monson",
      "to": "j.smith",
      "role": "designer",
      "scope": "substitutions_under_5000",
      "valid_from": "2026-03-15",
      "valid_to": "2026-03-22",
      "reason": "Out of office"
    }
  ]
}
```

### 6. Multi-Party Notification

Leverages the Collaboration Layer (Item 16) for notifications:

- **Slack/Teams** — Real-time approval request notifications
- **Email digest** — Daily summary of pending approvals
- **FIELD.html** — Badge count on mobile interface (Phase 4)
- **CLI** — `aecos approvals pending` shows outstanding items

## Architecture

### Module Structure
```
aecos/approvals/
├── __init__.py
├── gate_engine.py           # Approval gate definition and enforcement
├── workflow_engine.py       # State machine for approval workflows
├── signature_manager.py     # Cryptographic signing integration
├── escalation_engine.py     # Timeout and escalation logic
├── delegation_manager.py    # Proxy approval management
├── condition_tracker.py     # Conditional approval monitoring
├── notification_bridge.py   # Integration with Collaboration Layer
└── templates/
    ├── approval_request.md.j2
    ├── approval_decision.md.j2
    ├── escalation_notice.md.j2
    └── approval_matrix.md.j2
```

### AecOS Facade Integration
```python
# Submit for approval
os.request_approval(
    element_id="W-EXT-01",
    action="substitution",
    reference="SUB-001",
    requestor_role="contractor"
)

# Approve/reject
os.approve(approval_id="APR-001", decision="approved", conditions=["..."])
os.reject(approval_id="APR-001", reason="Does not meet fire rating")

# Query pending approvals
os.pending_approvals(role="designer")
os.approval_status(approval_id="APR-001")

# Delegate authority
os.delegate_approval(from_user="b.monson", to_user="j.smith", scope="...", duration_days=7)
```

### Data Flow
```
Action Requiring Approval (Phase 1, 2, or 6)
    ↓
Gate Engine → Determine required approvals from matrix
    ↓
Workflow Engine → Create approval chain
    ↓
Notification Bridge → Alert approvers (Slack/Teams/Email)
    ↓
Approver Decision → Signed commit via KeyManager
    ↓
Condition Tracker → Monitor attached conditions
    ↓
Escalation Engine → Handle timeouts
    ↓
AuditLogger (Item 17) → Full trail of every decision
```

### Element Folder Output
```
Elements/W-EXT-01/
├── ... (existing files)
├── approvals/
│   ├── APR-001_request.json       # Approval request
│   ├── APR-001_decision.json      # Signed decision
│   ├── APR-001_conditions.json    # Attached conditions + status
│   ├── APR-001_audit.json         # Full audit trail
│   └── APPROVAL_STATUS.md         # Human-readable summary
```

## Deliverables

- [ ] `aecos/approvals/` module with full workflow engine
- [ ] Configurable approval matrix per action type
- [ ] Cryptographic signing of all approval decisions
- [ ] Escalation engine with configurable timeouts
- [ ] Conditional approval tracking system
- [ ] Delegation and proxy approval management
- [ ] Integration with Collaboration Layer for notifications
- [ ] APPROVAL_STATUS.md generator per Element
- [ ] CLI command: `aecos approve <approval-id> --decision <approve|reject>`
- [ ] CLI command: `aecos approvals pending --role <role>`
- [ ] CLI command: `aecos delegate --to <user> --scope <scope> --days <n>`

## Testing Strategy

```bash
# Unit tests for gate and workflow engines
pytest tests/test_approvals.py

# Integration: Action → Gate → Notify → Approve → Commit
pytest tests/integration/test_approval_pipeline.py

# Escalation and timeout tests
pytest tests/test_approval_escalation.py

# Multi-party scenario tests
pytest tests/scenarios/test_multi_party_approval.py
```

## Bible Compliance Checklist

- [x] Local-first: Workflow engine runs locally, notifications are optional
- [x] Git SoT: Every approval decision is a signed Git commit
- [x] Pure-file: JSON decisions, Markdown summaries — no database
- [x] Cryptographic audit: KeyManager signs every approval
- [x] Revit compatible: Approval status attached to IFC element metadata
- [x] Legal/financial first: Signed approvals constitute legal record

---

**Dependency Chain:** Items 12, 16, 17 + Phases 1, 2, 6 → This Module
**Next Phase:** Phase 9 (Legal-Grade Audit and Chain-of-Custody Enhancements)
