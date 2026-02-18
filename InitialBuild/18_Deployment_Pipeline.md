**Deployment Pipeline (Roadmap Item 18)**  
**Goal:** Create a fully automated, repeatable, and secure deployment pipeline that transforms the complete `aecos` system—core package, template library, compliance database, fine-tuned models, vector index, and all supporting scripts—into a production-ready environment that can be deployed to individual workstations, team servers, cloud instances, or containerized clusters with a single command. The pipeline ensures consistent environments across Windows (for Revit/pyRevit users), Linux/macOS servers, and cloud platforms (AWS, GCP, Azure), while incorporating security controls (Item 17), version pinning, rollback capability, and zero-downtime updates for collaborative teams.

**Core Architecture**  
- **Packaging:** Modern Python packaging with `pyproject.toml` + `uv` or `pipx` for dependency isolation.  
- **Containerization:** Docker + Docker Compose for server/cloud deployments; optional Singularity/Apptainer for secure institutional environments.  
- **Orchestration:** GitHub Actions + self-hosted runners for CI/CD; Ansible/Terraform for infrastructure provisioning.  
- **Configuration Management:** Environment-specific `.env` templates and secrets management (HashiCorp Vault or GitHub Secrets).  
- **Output:** One-click installers, Docker images, and Helm charts (for Kubernetes teams).

**Prerequisites (1 hour)**  
- Completion of Roadmap Items 1–17.  
- `aecos` package fully tested in editable mode.  
- `pip install uv docker-compose ansible` (or equivalents).  
- GitHub repository with Actions already configured (Item 4).  
- Test Windows machine with Revit/pyRevit for desktop validation.

**Phase 1: Packaging and Dependency Locking (Day 1)**  
Finalize `pyproject.toml` with `uv` for reproducible locks:  
```toml
[project]
name = "aecos"
version = "1.0.0"
dependencies = [
    "ifcopenshell>=0.7.0",
    "langgraph",
    "ollama",
    # ... all prior requirements
]

[tool.uv]
dev-dependencies = ["pytest", "black"]
```
Generate `uv.lock` and publish to private PyPI or GitHub Packages:  
```bash
uv build
uv publish --index-url https://pypi.yourcompany.internal
```

**Phase 2: Docker Containerization (Day 1–2)**  
Create multi-stage Dockerfile:  
```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y git-crypt
COPY . .
RUN uv sync --frozen

FROM python:3.11-slim
COPY --from=builder /app /app
ENV PYTHONPATH=/app
CMD ["aecos", "serve"]
```
Docker Compose file for full stack (Ollama + FastAPI + PostgreSQL for collaboration data).

**Phase 3: CI/CD Pipeline (Day 2)**  
GitHub Actions workflow `.github/workflows/deploy.yml`:  
```yaml
name: Deploy AEC OS
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build & push Docker image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: yourcompany/aecos:${{ github.ref_name }}
  desktop-installer:
    runs-on: windows-latest
    steps:
      - name: Build Windows .exe installer (PyInstaller)
        run: pyinstaller --onefile --windowed aecos/cli.py
```

**Phase 4: Infrastructure as Code (Day 3)**  
Ansible playbook + Terraform modules for:  
- Cloud VM provisioning (AWS EC2 or GCP Compute Engine).  
- Automatic Ollama model download and fine-tuned model import.  
- Secure secrets injection via AWS Secrets Manager.

**Phase 5: One-Click Desktop & Server Installers (Day 3–4)**  
- Windows: NSIS or Inno Setup installer that installs Python, `aecos`, Ollama, and creates Start Menu shortcuts + pyRevit ribbon integration.  
- Linux/macOS: Shell script + Homebrew formula.  
- Cloud: One-command `aecos deploy cloud --provider aws --region us-east-1`.

**Phase 6: Rollback, Blue-Green, and Monitoring (Day 4)**  
- Blue-green deployment for zero-downtime server updates.  
- Automated rollback on failed health checks (e.g., parser accuracy test).  
- Prometheus + Grafana integration for system metrics (CPU/GPU usage, parse latency).

**Phase 7: Testing, Documentation, and Release (Day 5)**  
- End-to-end deployment tests on fresh Windows, Linux, and cloud instances.  
- Comprehensive deployment guide in `docs/deployment.md` with screenshots and troubleshooting.  
- Tagged release on GitHub with artifacts (Docker image, Windows installer, Helm chart).

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Executing `aecos deploy local` on a clean machine or `aecos deploy cloud --provider aws` on a new AWS account results in a fully functional AEC OS instance within 8 minutes, with all 17 prior modules operational, a live Speckle bridge, active Slack bot, and encrypted audit log confirming successful deployment. A subsequent `aecos deploy rollback --version 1.0.0` restores the previous state instantly.

This deployment pipeline eliminates environment inconsistencies and enables instant scaling from solo use to enterprise team deployments, completing the transition from personal prototype to production AEC operating system.

Implement Phases 1–3 today by finalizing the `pyproject.toml` and building the first Docker image. Should any questions arise regarding Windows installer specifics, cloud provider configuration, or CI/CD secrets handling, provide the relevant platform details for immediate refinement.
