**Version Control Backbone (Roadmap Item 4)**  
**Goal:** Establish a robust, git-based foundation for the entire system that ensures traceability, collaboration, safe experimentation, and automated quality gates across the template library (Item 2), extracted project data (Item 1), and generated Markdown metadata (Item 3). The repository structure treats IFC templates and project-derived elements as versioned artifacts, enabling branching for new regions/codes, releases for stable sets, and hooks for CI validation. This creates a single source of truth that scales to team use and future items (e.g., multi-user sync in Item 12).

**Repository Structure (Top-Level `aec-os` Repo)**
```
aec-os/
├── .github/
│   └── workflows/
│       ├── validate-templates.yml     # on push/PR: lint, schema check, geometry integrity
│       └── md-regenerate.yml          # auto-update READMEs on library changes
├── library/                           # Item 2: curated IFC templates
│   ├── index.json
│   ├── architectural/
│   │   └── walls/
│   │       └── concrete_150mm_fire2hr_ca_2025/
│   │           ├── template.ifc
│   │           ├── metadata.json
│   │           └── README.md
│   └── ... (structural, mep, etc.)
├── extracted/                         # Item 1: project-specific extractions (gitignore large ones or use LFS)
│   └── {project-guid}/
│       └── elements/
├── archive/                           # deprecated templates moved here with reason in README
├── scripts/                           # shared Python tools (extract, curate, generate_md)
├── docs/                              # high-level architecture, contribution guide
├── .gitignore                         # ignore large .ifc, temp files, __pycache__
└── README.md                          # repo overview, setup, quick commands
```

**Prerequisites (1 hour)**
- Git installed; Git LFS for .ifc files (`git lfs install`)
- GitHub/GitLab repo created as private initially
- `pip install pre-commit` (for local hooks)
- Existing Item 1–3 scripts

**Phase 1: Initialize & Configure Repo (Day 1)**
1. Create repo: `git init` or remote clone empty.
2. Add `.gitignore` (standard Python + large files):
   ```
   *.ifc  # unless using LFS
   *.obj
   __pycache__/
   *.log
   extracted/*/  # or selective
   ```
3. Enable Git LFS for binaries:
   ```
   git lfs track "*.ifc" "*.obj"
   git add .gitattributes
   ```
4. Set up conventional commits (optional but recommended for semantic versioning later):
   - Install commitizen or use template commits: `feat:`, `fix:`, `chore:`, `refactor:`

**Phase 2: Define Branching Strategy (Day 1)**
Adopt a simplified Gitflow variant optimized for library + project artifacts (inspired by AEC patterns: stable main, feature isolation, release tags):
- **main** — Production-ready templates and tools (protected branch; only merge via PR)
- **develop** — Integration branch for ongoing work (all features merge here first)
- **feature/*** — Short-lived branches for new templates, fixes, or enhancements (e.g., `feature/add-steel-beam-eu-ibc2024`)
- **hotfix/*** — Urgent fixes to main (e.g., compliance update)
- **release/**vX.Y.Z** — Preparation for tagged releases (bump versions, finalize docs)
- **archive/*** — Rarely used; for moving deprecated content

Workflow:
- New template/compliance update → create `feature/...` from `develop`
- Complete → PR to `develop` (auto-run validation)
- Stable set ready → create `release/v1.2.0` from `develop`, tag, merge to `main`
- Tag pushes trigger release artifacts (e.g., zipped library subset)

Protect branches in GitHub: require PR reviews, status checks passing.

**Phase 3: Add Quality Gates & Hooks (Day 2)**
1. Local pre-commit hooks:
   ```
   pre-commit install
   ```
   Sample `.pre-commit-config.yaml`:
   ```yaml
   repos:
   - repo: https://github.com/pre-commit/pre-commit-hooks
     rev: v4.4.0
     hooks:
     - id: check-yaml
     - id: end-of-file-fixer
   - repo: local
     hooks:
     - id: validate-json
       name: Validate metadata.json
       entry: python scripts/validate_schema.py
       language: system
       files: ^library/.*/metadata\.json$
   ```
2. GitHub Actions (`.github/workflows/validate-templates.yml`):
   ```yaml
   name: Validate Templates
   on: [push, pull_request]
   jobs:
     validate:
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v4
       - name: Set up Python
         uses: actions/setup-python@v5
         with: { python-version: '3.11' }
       - run: pip install ifcopenshell pandas jsonschema
       - run: python scripts/validate_library.py  # check schema, duplicate GUIDs, etc.
       - run: python scripts/check_md_density.py  # ensure READMEs <60 lines, have key sections
   ```
3. Markdown auto-regen on library push (separate workflow).

**Phase 4: Tagging & Release Process (Day 3)**
- Semantic versioning: vMAJOR.MINOR.PATCH
  - MAJOR: breaking changes (e.g., schema update IFC4 → IFC4.3)
  - MINOR: new templates/regions
  - PATCH: fixes, metadata updates
- Tag command: `git tag -a v1.0.0 -m "Initial stable library release"`
- GitHub Releases: attach zipped subsets (e.g., `architectural-only.zip`) for quick import.

**Phase 5: Collaboration & Scaling (Day 4)**
- Branch protection rules + required reviewers
- Issue templates for new template requests
- Pull request template: checklist for compliance links, test in Revit, etc.
- For large teams: add CODEOWNERS file (e.g., @your-username for /library/architectural/)

**Phase 6: Testing & Iteration (Day 4–5)**
- Simulate workflow: create feature branch, add dummy template, PR to develop, merge, tag release
- Test LFS: push/pull large .ifc → confirm tracking
- Validate CI: force fail on bad JSON → confirm block
- Metrics: `git log --oneline | wc -l` for activity; aim for clean history

**Total time to working v1 (protected main + CI):** 5 days  
**Milestone check:** You can safely create a feature branch, add a new template, merge via PR (CI passes), tag a release, and pull the updated `main` on another machine—all with full history and no lost changes.

This backbone ensures every change is auditable and reversible, preparing for multi-user (Item 12) and automated updates (Item 15).  

Implement Phase 1–2 today and share your repo structure (or any errors)—I will refine the workflows or .pre-commit config accordingly.