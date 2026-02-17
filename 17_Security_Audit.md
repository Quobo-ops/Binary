**Security & Audit (Roadmap Item 17)**  
**Goal:** Develop a comprehensive, enterprise-grade security and audit framework that safeguards all assets within the AEC OS, enforces strict access controls, and maintains an immutable, cryptographically verifiable record of every action taken across the system. This module builds directly upon the version-control backbone (Item 4), multi-user synchronization (Item 12), collaboration layer (Item 16), fine-tuning loop (Item 13), and regulatory auto-update (Item 15). It ensures compliance with relevant standards (AIA Contract Documents, ISO 27001, SOC 2 Type II, and client-specific data-security requirements), protects proprietary templates and fine-tuned models, and delivers auditable evidence suitable for professional liability, insurance, and legal review.

**Core Architecture**  
- **Encryption Layer:** Selective, transparent encryption of sensitive files (.ifc, .json, model weights, cost data) using git-crypt and age.  
- **Audit Trail:** Append-only, digitally signed SQLite database with SHA-256 hashing and RSA/Ed25519 signatures on every entry.  
- **Access Control:** Role-based access control (RBAC) enforced at repository, folder, and element levels.  
- **Approval Workflows:** Mandatory electronic sign-off for merges, model promotions, and regulatory updates.  
- **Monitoring & Alerts:** Real-time anomaly detection and integration with collaboration notifications (Item 16).  

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–16.  
- `aecos` package installed in editable mode.  
- `pip install cryptography git-crypt structlog pynacl python-jose passlib`  
- GitHub/GitLab repository with branch protection rules already configured.  
- Team member public keys or GPG identities collected for encryption.

**Phase 1: Encryption Implementation (Day 1)**  
Initialize git-crypt and configure `.gitattributes` for automatic encryption of binary and sensitive text files.  
Create `aecos/security/encryption_manager.py`:  
```python
from age import Age
from pathlib import Path

class EncryptionManager:
    def encrypt_folder(self, folder: Path, recipients: list[str]):
        age = Age()
        for file in folder.rglob("*"):
            if file.suffix in {".ifc", ".json", ".bin"}:
                encrypted = age.encrypt(file.read_bytes(), recipients)
                file.write_bytes(encrypted)
```
Integrate as a pre-commit hook.

**Phase 2: Immutable Audit Logging (Day 1–2)**  
Implement `aecos/security/audit_logger.py`:  
```python
import structlog
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from datetime import datetime
import sqlite_utils

class AuditLogger:
    def __init__(self):
        self.db = sqlite_utils.Database("audit.db")
        self.private_key = rsa.generate_private_key(...)  # or load from secure store

    def log(self, user: str, action: str, resource: str, before_hash: str = None, after_hash: str = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "action": action,
            "resource": resource,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "signature": self._sign_entry(...)
        }
        self.db["events"].insert(entry)
        structlog.get_logger().info("audit", **entry)
```
Log every parser call, generation, validation, collaboration event, and model training step.

**Phase 3: Role-Based Access Control & Workflows (Day 2–3)**  
Define roles in `.aecos/roles.json` (Architect, Structural Engineer, BIM Coordinator, Reviewer, Guest).  
Extend GitHub Actions with required-reviewer checks and integrate with collaboration bot (Item 16) for Slack/Teams approval commands:  
```bash
/aecos approve element_123 --role reviewer
```

**Phase 4: Key Management & Rotation (Day 3)**  
Automated 90-day key rotation script with audit-logged notification and secure backup to hardware token or encrypted vault.

**Phase 5: Anomaly Detection & Reporting (Day 4)**  
Add lightweight rules (e.g., unusual access patterns, bulk deletions) that trigger immediate alerts via the collaboration layer.  
Generate monthly `SECURITY_REPORT.md` and PDF exports suitable for client or insurer submission.

**Phase 6: CLI & Automated Hooks (Day 4)**  
```bash
aecos security audit --resource generated/wall_123
aecos security encrypt --all
aecos security scan
```
Automatic enforcement on every `git commit`, `aecos generate`, and `aecos sync`.

**Phase 7: Testing, Validation & Maintenance (Day 5)**  
- Simulated penetration scenarios (unauthorized access, log tampering, key compromise).  
- Test suite: 80 scenarios verifying 100 % logging coverage and signature validation.  
- Annual policy review workflow with built-in checklist.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After generating a test element, the system produces an encrypted folder, a cryptographically signed audit entry for every step (parse → generate → collaborate → approve), and a complete security report confirming zero critical findings. All changes are traceable in the immutable log, with rollback capability to any prior signed state.

This security and audit framework completes the enterprise readiness of the AEC OS, providing the defensibility and trust required for professional practice and team-scale deployment while preserving the speed and simplicity of earlier roadmap stages.

Implement Phases 1–3 today on a test branch. Should any questions arise regarding key generation, signature implementation, or workflow integration, provide the relevant details for immediate refinement.
