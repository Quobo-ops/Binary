# Phase 9: Legal-Grade Audit and Chain-of-Custody Enhancements
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 4 (VCS), 17 (Security & Audit); Phases 1–8 (all prior contractor capabilities)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Strengthens cryptographic signing and immutable logging to produce court- and insurer-ready chain-of-custody records for every Element across its full lifecycle. This elevates the existing audit system (Item 17) from operational logging to legal-grade evidence that meets the standards of professional liability insurers, courts, and regulatory bodies.

## Goal

Make every action in the AEC OS digital thread admissible as legal evidence. Produce chain-of-custody records that satisfy AIA Contract Document standards, ISO 27001 audit requirements, SOC 2 Type II evidence criteria, and Louisiana Professional Engineering Board documentation standards.

## Core Capabilities

### 1. Enhanced Cryptographic Signing

Upgrades the existing KeyManager (Item 17) with:

- **Timestamping Authority (TSA)** — RFC 3161 compliant timestamps proving when a signature was created (optional external service, with local fallback)
- **Certificate chain** — Full PKI chain from individual key → firm certificate → root CA
- **Multi-signature** — Support for co-signing (designer + contractor on same document)
- **Non-repudiation** — Signatures that cannot be disavowed by the signer
- **Key rotation** — Automatic key rotation with backward-compatible verification

```json
{
  "signature_envelope": {
    "payload_hash": "SHA-256:a1b2c3d4...",
    "signer": {
      "name": "Brennen Monson, AIA",
      "role": "designer",
      "license": "LA-12345",
      "key_id": "KEY-2026-001",
      "certificate_chain": ["personal.pem", "firm.pem", "root.pem"]
    },
    "timestamp": {
      "time": "2026-03-15T14:32:00.000Z",
      "source": "local_monotonic",
      "tsa_receipt": null
    },
    "algorithm": "Ed25519",
    "signature": "base64:...",
    "counter_signatures": []
  }
}
```

### 2. Merkle Tree Integrity Verification

Complete project-level integrity proof:

```
Project Merkle Tree:
  Root Hash: SHA-256:xyz789...
    ├── Element W-EXT-01 Hash: abc123...
    │   ├── Design data hash
    │   ├── Substitution SUB-001 hash
    │   ├── As-built AB-001 hash
    │   ├── Change order CO-007 hash
    │   └── Approval APR-001 hash
    ├── Element D-101 Hash: def456...
    │   └── ...
    └── Element S-102 Hash: ghi789...
        └── ...

Verification: Any single bit change in any file invalidates the chain.
```

### 3. Chain-of-Custody Records

Formal custody transfer documentation for every element:

```markdown
## Chain of Custody: W-EXT-01

| # | Action | Custodian | Date | Signature |
|---|--------|-----------|------|-----------|
| 1 | Created from template | B. Monson (Designer) | 2026-01-15 | ✅ Verified |
| 2 | Spec reviewed | J. Smith (Reviewer) | 2026-01-18 | ✅ Verified |
| 3 | Released to contractor | B. Monson → Smith Bros | 2026-02-01 | ✅ Verified |
| 4 | Substitution proposed | T. Garcia (Contractor) | 2026-02-20 | ✅ Verified |
| 5 | Substitution approved | B. Monson (Designer) | 2026-02-21 | ✅ Verified |
| 6 | Material procured | Smith Bros (Contractor) | 2026-02-25 | ✅ Verified |
| 7 | Installed as-built | J. Garcia (Foreman) | 2026-03-05 | ✅ Verified |
| 8 | Deviation logged | J. Garcia (Foreman) | 2026-03-05 | ✅ Verified |
| 9 | Deviation accepted | B. Monson (Designer) | 2026-03-06 | ✅ Verified |
| 10 | Final inspection | Parish Inspector #4421 | 2026-03-10 | ✅ Verified |
| 11 | Handed over to owner | B. Monson → Owner LLC | 2026-04-01 | ✅ Verified |

**Integrity Status:** ✅ UNBROKEN CHAIN — All 11 entries verified
**Merkle Proof:** Valid against project root hash
```

### 4. Legal Export Formats

Production of court-admissible documentation:

| Format | Purpose | Standard |
|--------|---------|----------|
| Signed PDF/A | Long-term archival, court submission | ISO 19005 (PDF/A-3) |
| Evidence Package (.zip) | Complete discoverable evidence set | FRCP Rule 34 |
| Expert Report Template | Pre-formatted for expert witness testimony | AIA/ACEC |
| Insurance Submission | Claims documentation package | ISO 27001 Annex A |
| Regulatory Filing | Board complaint response documentation | State PE Board |

### 5. Tamper Detection and Alerting

Active monitoring for unauthorized modifications:

```python
class TamperDetector:
    def verify_chain(self, element_folder: Path) -> VerificationResult:
        """Verify complete chain-of-custody integrity."""
        # Recompute all hashes from source files
        # Compare against stored Merkle tree
        # Verify all signatures against certificate chain
        # Check for gaps in sequence numbers
        # Detect any unsigned modifications
        return VerificationResult(
            status="INTACT" | "TAMPERED" | "GAP_DETECTED",
            details=[...],
            last_verified=datetime.now()
        )
```

### 6. Retention and Archival Policies

Configurable retention rules per jurisdiction:

```json
{
  "retention_policies": {
    "louisiana": {
      "construction_records": "10_years",
      "professional_liability": "statute_of_repose_10_years",
      "tax_records": "7_years",
      "insurance_claims": "until_resolved_plus_3_years"
    },
    "federal": {
      "ada_compliance": "indefinite",
      "environmental": "30_years",
      "osha_records": "5_years"
    }
  }
}
```

## Architecture

### Module Structure
```
aecos/audit/
├── __init__.py
├── enhanced_signer.py       # Upgraded cryptographic signing
├── merkle_tree.py           # Project-wide Merkle tree builder
├── chain_of_custody.py      # Formal custody record manager
├── tamper_detector.py       # Integrity verification engine
├── legal_exporter.py        # Court-ready document generator
├── retention_manager.py     # Archival policy enforcement
├── tsa_client.py            # RFC 3161 timestamp authority client
└── templates/
    ├── chain_of_custody.md.j2
    ├── evidence_package.md.j2
    ├── integrity_report.md.j2
    └── expert_report.md.j2
```

### AecOS Facade Integration
```python
# Verify integrity
os.verify_chain_of_custody(element_id="W-EXT-01")
os.verify_project_integrity(project_id="XYZ")

# Generate legal exports
os.export_evidence_package(element_id="W-EXT-01", format="court_submission")
os.export_insurance_package(project_id="XYZ")

# Merkle tree operations
os.build_merkle_tree(project_id="XYZ")
os.verify_merkle_proof(element_id="W-EXT-01")

# Retention management
os.check_retention_status(project_id="XYZ", jurisdiction="louisiana")
```

## Deliverables

- [ ] `aecos/audit/` enhanced module with legal-grade capabilities
- [ ] Merkle tree builder for project-wide integrity verification
- [ ] Chain-of-custody record generator per element
- [ ] Tamper detection engine with alerting
- [ ] Legal export formats (PDF/A, evidence package, expert report)
- [ ] RFC 3161 timestamp authority client (optional external, local fallback)
- [ ] Multi-signature support for co-signing workflows
- [ ] Retention policy manager with jurisdiction-aware rules
- [ ] CLI command: `aecos audit verify <element-id>`
- [ ] CLI command: `aecos audit chain-of-custody <element-id>`
- [ ] CLI command: `aecos audit export --format evidence_package`
- [ ] CLI command: `aecos audit merkle-tree build --project <id>`

## Testing Strategy

```bash
# Unit tests for crypto operations and Merkle tree
pytest tests/test_audit_legal.py

# Integration: Full lifecycle → Chain-of-custody verification
pytest tests/integration/test_chain_of_custody.py

# Tamper detection: Intentionally corrupt data, verify detection
pytest tests/test_tamper_detection.py

# Signature verification across key rotation
pytest tests/test_key_rotation.py
```

## Bible Compliance Checklist

- [x] Local-first: All verification and signing runs locally (TSA optional)
- [x] Git SoT: Audit data versioned in Git alongside element data
- [x] Pure-file: JSON audit logs, Markdown reports, signed PDFs
- [x] Cryptographic audit: Core purpose of this phase
- [x] Revit compatible: Audit metadata linkable to IFC element GUIDs
- [x] Legal/financial first: Core purpose — court-admissible evidence

---

**Dependency Chain:** Items 4, 17 + Phases 1–8 → This Module
**Next Phase:** Phase 10 (Live Project Intelligence Dashboard)
