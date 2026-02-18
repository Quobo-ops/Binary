**Regulatory Auto-Update (Roadmap Item 15)**  
**Goal:** Establish an automated, scheduled process that continuously monitors authoritative sources for amendments, errata, and new editions of building codes and standards (International Building Code, California Building Code, Title 24, ASCE 7, ASHRAE 90.1, NEC, and applicable local amendments). The system ingests changes, updates the compliance database (Item 7), re-tags and re-validates affected templates in the library (Item 2), regenerates associated Markdown metadata (Item 3), triggers fine-tuning examples where appropriate (Item 13), and propagates notifications through the multi-user sync and collaboration layers (Items 12 and 16). This ensures perpetual regulatory compliance across the entire AEC OS without manual intervention while preserving complete auditability (Item 13) and version history (Item 4).

**Core Architecture**  
- **Monitoring Agents:** Dedicated scrapers and API clients for official publishers (ICC, California Building Standards Commission, ASHRAE, etc.).  
- **Change Detection:** Diff-based comparison of regulatory text and tables against cached versions.  
- **Impact Analysis:** Automated mapping of changes to IFC classes, performance attributes, and existing templates.  
- **Update Pipeline:** Atomic updates to SQLite compliance database, library tags, and Markdown files, followed by optional model fine-tuning triggers.  
- **Notification & Rollback:** Slack/Teams/Discord alerts with one-click rollback via git tags.

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–14.  
- `aecos` package installed in editable mode.  
- `pip install beautifulsoup4 requests lxml schedule difflib pandas pypdf2` (for scraping and PDF parsing).  
- API keys or credentials for premium sources (e.g., ICC Digital Codes API, Gordian RSMeans) stored securely in `.env`.  
- Compliance database (Item 7) and library index (Item 2) already populated.

**Phase 1: Monitoring Configuration (Day 1)**  
Create `aecos/regulatory/monitor.py`:  
```python
import schedule
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SOURCES = {
    "CBC": "https://codes.iccsafe.org/content/CBC2025P2",
    "Title24": "https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards",
    # Add RSS feeds or API endpoints for IBC, ASCE, etc.
}

def check_for_updates():
    for code, url in SOURCES.items():
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "lxml")
        latest_version = extract_version(soup)  # custom parser
        if latest_version > cached_version(code):
            trigger_ingestion(code, latest_version)
```

Configure as a background service or GitHub Actions cron (weekly on Sunday 02:00 UTC).

**Phase 2: Change Ingestion and Diff Engine (Day 1–2)**  
Extend the ingestion pipeline from Item 7:  
```python
def ingest_amendment(pdf_url: str, code_name: str):
    # Download, extract text/tables using pdfplumber
    new_rules = parse_new_provisions(pdf_content)
    db = sqlite_utils.Database("compliance.db")
    changes = diff_rules(db, new_rules)  # section-by-section comparison
    for change in changes:
        db["rules"].upsert(change)
        tag_affected_templates(change)
```

**Phase 3: Impact Analysis and Template Re-Tagging (Day 2)**  
```python
def tag_affected_templates(change: dict):
    affected = aecos.core.library.find_templates_by_rule(change["section"])
    for template_path in affected:
        update_tags(template_path, change)
        aecos.core.markdown.generate_markdown(template_path)  # refresh README/COMPLIANCE
        aecos.validation.run_full_validation(template_path)   # re-validate
```

**Phase 4: Notification and Versioning (Day 3)**  
Integrate with notifier (Item 12):  
```python
send_notification({
    "type": "regulatory_update",
    "code": code_name,
    "changed_sections": changed_list,
    "affected_templates": len(affected),
    "git_tag": f"reg-update-{code_name}-{date}"
})
```
Create git tag and protected release branch for each update.

**Phase 5: Fine-Tuning Trigger and Audit Logging (Day 3–4)**  
- If compliance rules change materially, auto-generate 20–50 new training examples for the fine-tuning loop (Item 13).  
- Every update is logged in the tamper-evident audit database (Item 13) with before/after hashes.

**Phase 6: CLI and Manual Override (Day 4)**  
```bash
aecos regulatory check-updates --force
aecos regulatory rollback --tag reg-update-CBC-2026-02-10
```

**Phase 7: Testing, Reliability, and Maintenance (Day 5)**  
- Simulation suite: 30 synthetic amendments tested end-to-end (target 100 % detection and correct re-tagging).  
- False-positive filter for non-substantive errata.  
- Annual review of scraper robustness against website layout changes.  
- Fallback manual upload interface for offline or proprietary codes.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After configuring the weekly schedule and simulating one code amendment (e.g., CBC 2025 errata affecting fire-rating tables), the system automatically updates the compliance database, re-tags 15 affected wall and door templates, regenerates their Markdown files, commits the changes under a signed git tag, and delivers a detailed notification to the team channel with direct links to updated elements and rollback instructions.

This regulatory auto-update capability ensures the AEC OS remains a living, compliant design environment that evolves in lockstep with the regulatory landscape, eliminating the risk of outdated templates and significantly reducing compliance review effort.

Implement Phases 1–3 today by setting up the monitoring script for a single code (CBC or IBC) and testing the ingestion on a known recent amendment. Should any challenges arise with scraping logic or impact-analysis mapping, provide the relevant source URLs or sample PDFs for targeted refinement.
