# Phase 17: Secure, Optional Ecosystem Integrations
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 5 (API Wrapper), 10 (Cost), 11 (Visualization), 16 (Collaboration), 17 (Security & Audit); Phases 7 (4D/5D), 10 (Dashboard)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Adds local-cached, bidirectional connectors to Procore, Autodesk Construction Cloud, ERP systems, and other platforms, with explicit user-controlled data flow and offline fallbacks. These integrations are strictly optional — the system operates fully without them — but when enabled, they eliminate double-entry and bridge AEC OS to the tools contractors and owners already use.

## Goal

Enable AEC OS to exchange data with the most common AEC industry platforms without compromising local-first operation, data sovereignty, or audit integrity. Every integration follows the same pattern: local cache first, explicit user consent for data flow, and full operation when the external service is unavailable.

## Core Design Principles (Integration-Specific)

1. **Optional always** — AEC OS functions 100% without any integration enabled
2. **User-controlled data flow** — No data leaves the system without explicit user action
3. **Local cache first** — All external data cached locally; operations continue offline
4. **Bidirectional with conflict resolution** — Push and pull with merge strategy
5. **Audit every exchange** — Every data transfer logged with source, destination, payload hash
6. **Credential isolation** — API keys stored in encrypted local keystore, never in Git

## Supported Integrations

### 1. Procore (Construction Management)

```
AEC OS ←→ Procore
  Push: Schedule updates, RFIs, change orders, daily logs
  Pull: Submittals, drawings, inspection reports, budget data
  Sync: Bidirectional element status updates
```

| Data Type | Direction | Format | Trigger |
|-----------|-----------|--------|---------|
| Schedule activities | Push | CSV/API | `aecos sync procore schedule` |
| Change orders | Push | PDF + API | On CO approval (Phase 6) |
| RFI responses | Pull | API → JSON | On-demand or scheduled |
| Budget line items | Pull | API → JSON | On-demand |
| Daily logs | Push | API | On field-log commit (Phase 2) |
| Submittal status | Bidirectional | API | Scheduled sync |

### 2. Autodesk Construction Cloud (ACC)

```
AEC OS ←→ ACC
  Push: IFC models, element status, compliance reports
  Pull: Revit model updates, markups, issue tracking
  Sync: Model coordination and clash status
```

| Data Type | Direction | Format | Trigger |
|-----------|-----------|--------|---------|
| IFC exports | Push | IFC 2x3/4x3 | On element update |
| Design reviews | Pull | API → JSON | On-demand |
| Issues/markups | Bidirectional | API | Scheduled sync |
| Sheet sets | Push | PDF | On-demand |
| Model versions | Pull | API → IFC | On-demand |

### 3. ERP / Accounting Systems

```
AEC OS ←→ Sage 300 / QuickBooks / Other
  Push: Cost data, change orders, payment applications
  Pull: Actual costs, vendor payments, budget updates
```

| Data Type | Direction | Format | Trigger |
|-----------|-----------|--------|---------|
| Cost estimates | Push | CSV | On cost calculation |
| Change orders | Push | CSV/PDF | On CO approval |
| Payment applications | Push | AIA G702/703 CSV | On request |
| Actual costs | Pull | CSV import | Monthly reconciliation |
| Vendor data | Pull | CSV import | On-demand |

### 4. Scheduling Tools (Primavera P6, MS Project)

```
AEC OS ←→ P6 / MS Project
  Push: Activity updates, progress, resource changes
  Pull: Baseline schedule, constraints, calendars
  Sync: Critical path and float updates
```

### 5. BIM Coordination (Navisworks, Solibri)

```
AEC OS ←→ Navisworks / Solibri
  Push: IFC models, clash rules, element metadata
  Pull: Clash reports, coordination issues
```

### 6. Communication (Slack, Teams, Email)

Already established in Item 16; this phase adds:
- Structured approval notifications with inline action buttons
- Automated daily digest emails
- Webhook receivers for external event triggers

## Architecture

### Module Structure
```
aecos/integrations/
├── __init__.py
├── base_connector.py        # Abstract base for all connectors
├── sync_engine.py           # Bidirectional sync with conflict resolution
├── cache_manager.py         # Local cache for all external data
├── credential_store.py      # Encrypted credential management
├── data_flow_controller.py  # User-controlled data flow enforcement
├── audit_bridge.py          # Integration-specific audit logging
├── connectors/
│   ├── __init__.py
│   ├── procore.py           # Procore API connector
│   ├── acc.py               # Autodesk Construction Cloud connector
│   ├── sage.py              # Sage 300 ERP connector
│   ├── quickbooks.py        # QuickBooks connector
│   ├── primavera.py         # P6 API connector
│   ├── ms_project.py        # MS Project connector
│   ├── navisworks.py        # Navisworks connector
│   └── email.py             # SMTP/IMAP email connector
└── config/
    ├── integration_manifest.json   # Available integrations
    ├── data_flow_rules.json       # What data can flow where
    └── sync_schedules.json        # Automated sync timing
```

### Base Connector Pattern
```python
class BaseConnector(ABC):
    """All integrations follow this pattern."""

    def __init__(self, config: dict):
        self.cache = CacheManager(self.name)
        self.credentials = CredentialStore.get(self.name)
        self.audit = AuditBridge(self.name)

    def push(self, data: dict, data_type: str) -> SyncResult:
        """Push data to external system with full audit."""
        # Validate user has authorized this data flow
        self.data_flow_controller.validate(data_type, direction="push")
        # Cache locally first
        self.cache.store(data, data_type)
        # Attempt push (with retry on network failure)
        try:
            result = self._push_impl(data, data_type)
            self.audit.log_push(data_type, result)
            return result
        except NetworkError:
            self.cache.mark_pending(data, data_type)
            return SyncResult(status="queued", message="Will retry when online")

    def pull(self, data_type: str) -> dict:
        """Pull data from external system into local cache."""
        self.data_flow_controller.validate(data_type, direction="pull")
        try:
            data = self._pull_impl(data_type)
            self.cache.store(data, data_type)
            self.audit.log_pull(data_type, data)
            return data
        except NetworkError:
            return self.cache.get_latest(data_type)  # Return cached version
```

### Data Flow Control
```json
{
  "data_flow_rules": {
    "procore": {
      "push_allowed": ["schedule", "change_orders", "daily_logs"],
      "pull_allowed": ["submittals", "budget", "rfis"],
      "push_blocked": ["audit_logs", "internal_notes", "financial_details"],
      "requires_approval": ["cost_data", "compliance_reports"],
      "auto_sync": false,
      "sync_schedule": null
    }
  }
}
```

### AecOS Facade Integration
```python
# Configure integration
os.enable_integration("procore", credentials={...})
os.disable_integration("procore")

# Manual sync
os.sync("procore", data_type="schedule", direction="push")
os.sync("procore", data_type="submittals", direction="pull")

# Sync status
os.sync_status("procore")
os.pending_syncs()

# Data flow management
os.data_flow_rules("procore")
os.update_data_flow("procore", "push_allowed", ["schedule", "daily_logs"])
```

### Offline Behavior
```
Normal operation (online):
  AEC OS → Connector → External API → Success → Audit log

Offline operation:
  AEC OS → Connector → Cache (queued) → Audit log (pending)
  ... connectivity restored ...
  Cache → Connector → External API → Success → Audit log (completed)
  Conflict? → Flag for manual resolution
```

## Deliverables

- [ ] `aecos/integrations/` module with connector framework
- [ ] Procore connector (schedule, CO, daily logs, submittals, budget)
- [ ] Autodesk Construction Cloud connector (IFC, issues, reviews)
- [ ] ERP connector framework (Sage 300, QuickBooks templates)
- [ ] Scheduling tool connectors (P6, MS Project)
- [ ] Encrypted credential store (never in Git)
- [ ] User-controlled data flow rules engine
- [ ] Local cache with offline queue and auto-retry
- [ ] Conflict detection and resolution UI
- [ ] Integration-specific audit logging
- [ ] CLI command: `aecos integrate enable <platform>`
- [ ] CLI command: `aecos sync <platform> <data-type> --direction <push|pull>`
- [ ] CLI command: `aecos sync status`
- [ ] CLI command: `aecos integrate data-flow <platform>`

## Testing Strategy

```bash
# Unit tests for connector framework and cache
pytest tests/test_integrations.py

# Mock API tests for each connector
pytest tests/test_procore_connector.py
pytest tests/test_acc_connector.py

# Offline/online transition tests
pytest tests/test_integration_offline.py

# Data flow enforcement tests
pytest tests/test_data_flow_control.py
```

## Bible Compliance Checklist

- [x] Local-first: Full operation without any integration enabled
- [x] Git SoT: Cached external data stored as versioned files, never replaces Git data
- [x] Pure-file: Cache as JSON files, credentials in encrypted local store
- [x] Cryptographic audit: Every data exchange logged with payload hash
- [x] Revit compatible: IFC push/pull maintains Revit linkability
- [x] Legal/financial first: User controls all data flow, audit trail on every exchange

---

**Dependency Chain:** Items 5, 10, 11, 16, 17 + Phases 7, 10 → This Module
**Next Phase:** Phase 18 (Commercial Packaging and Distribution Strategy)
