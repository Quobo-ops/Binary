"""CIGenerator — generates GitHub Actions workflow files."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_WORKFLOW_TEMPLATE = """\
name: AEC OS CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check aecos/ tests/

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}
          cache: pip
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ -v --tb=short

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Build package
        run: |
          pip install build
          python -m build
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
"""


class CIGenerator:
    """Generate CI/CD configuration files."""

    def generate_github_actions(self, project_path: str | Path) -> Path:
        """Write .github/workflows/ci.yml.

        Returns the path to the generated file.
        """
        root = Path(project_path)
        workflow_dir = root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        path = workflow_dir / "ci.yml"
        path.write_text(_WORKFLOW_TEMPLATE, encoding="utf-8")
        logger.info("GitHub Actions workflow generated: %s", path)
        return path
