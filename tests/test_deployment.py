"""Tests for Item 18 — Deployment Pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

from aecos.deployment.ci import CIGenerator
from aecos.deployment.config_manager import ConfigManager
from aecos.deployment.docker import DockerBuilder
from aecos.deployment.health import HealthChecker, HealthReport
from aecos.deployment.installer import Installer
from aecos.deployment.packager import SystemPackager
from aecos.deployment.rollback import RollbackManager


# ── SystemPackager ───────────────────────────────────────────────────────────

class TestSystemPackager:

    def test_package_creates_archive_with_manifest(self):
        packager = SystemPackager()
        with tempfile.TemporaryDirectory() as project:
            # Create minimal project structure
            (Path(project) / "aecos").mkdir()
            (Path(project) / "aecos" / "__init__.py").write_text("version = '1.0.0'")
            (Path(project) / "pyproject.toml").write_text('[project]\nversion = "1.0.0"')
            (Path(project) / "README.md").write_text("# AEC OS")

            with tempfile.TemporaryDirectory() as out_dir:
                archive = packager.package(project, Path(out_dir) / "aecos.tar.gz")
                assert archive.is_file()
                assert archive.name == "aecos.tar.gz"

                # Verify manifest exists beside archive
                manifest = Path(out_dir) / "package_manifest.json"
                assert manifest.is_file()
                data = json.loads(manifest.read_text())
                assert "files" in data
                assert len(data["files"]) >= 3

    def test_package_excludes_git_and_pycache(self):
        packager = SystemPackager()
        with tempfile.TemporaryDirectory() as project:
            (Path(project) / "src.py").write_text("x = 1")
            git_dir = Path(project) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("git config")
            cache_dir = Path(project) / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "src.cpython-312.pyc").write_bytes(b"\x00")

            with tempfile.TemporaryDirectory() as out_dir:
                archive = packager.package(project, Path(out_dir) / "pkg.tar.gz")

                with tarfile.open(archive, "r:gz") as tar:
                    names = tar.getnames()
                    assert not any(".git" in n for n in names if n != "package_manifest.json")
                    assert not any("__pycache__" in n for n in names)


# ── Installer ────────────────────────────────────────────────────────────────

class TestInstaller:

    def test_verify_package_valid(self):
        packager = SystemPackager()
        installer = Installer()

        with tempfile.TemporaryDirectory() as project:
            (Path(project) / "data.txt").write_text("hello world")

            with tempfile.TemporaryDirectory() as out_dir:
                archive = packager.package(project, Path(out_dir) / "pkg.tar.gz")
                assert installer.verify_package(archive) is True

    def test_verify_package_invalid(self):
        installer = Installer()

        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "fake.tar.gz"
            fake.write_bytes(b"not a real archive")
            assert installer.verify_package(fake) is False

    def test_install_extracts_files(self):
        packager = SystemPackager()
        installer = Installer()

        with tempfile.TemporaryDirectory() as project:
            (Path(project) / "main.py").write_text("print('hello')")
            (Path(project) / "pyproject.toml").write_text(
                '[project]\nversion = "1.0.0"'
            )

            with tempfile.TemporaryDirectory() as out_dir:
                archive = packager.package(project, Path(out_dir) / "pkg.tar.gz")

                with tempfile.TemporaryDirectory() as target:
                    result = installer.install(archive, target)
                    assert result.success is True
                    assert result.version == "1.0.0"


# ── HealthChecker ────────────────────────────────────────────────────────────

class TestHealthChecker:

    def test_healthy_project(self):
        checker = HealthChecker()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            (root / "elements").mkdir()
            (root / "templates").mkdir()

            report = checker.check(root)
            assert isinstance(report, HealthReport)
            # At minimum python version and git should pass
            assert report.status in ("healthy", "degraded")

    def test_missing_git_degrades(self):
        checker = HealthChecker()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "elements").mkdir()
            (root / "templates").mkdir()

            report = checker.check(root)
            git_check = next(c for c in report.checks if c.name == "git_repo")
            assert git_check.passed is False

    def test_check_all_modules(self):
        checker = HealthChecker()
        results = checker.check_all_modules()
        # All modules should be importable
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0, f"Failed modules: {[r.name for r in failed]}"


# ── ConfigManager ────────────────────────────────────────────────────────────

class TestConfigManager:

    def test_generate_env_template(self):
        mgr = ConfigManager()
        with tempfile.TemporaryDirectory() as d:
            path = mgr.generate_env_template(d)
            assert path.is_file()
            content = path.read_text()
            assert "AECOS_ENV" in content
            assert "OLLAMA_HOST" in content
            assert "SPECKLE_TOKEN" in content
            assert "AECOS_AUDIT_DB" in content
            assert "AECOS_ANALYTICS_DB" in content

    def test_load_config_defaults(self):
        mgr = ConfigManager()
        with tempfile.TemporaryDirectory() as d:
            config = mgr.load_config(d)
            assert "AECOS_ENV" in config
            assert config["AECOS_LOG_LEVEL"] in ("DEBUG", "INFO", "WARNING")

    def test_load_config_merges_json(self):
        mgr = ConfigManager()
        with tempfile.TemporaryDirectory() as d:
            aecos_dir = Path(d) / ".aecos"
            aecos_dir.mkdir()
            (aecos_dir / "config.json").write_text(
                json.dumps({"CUSTOM_KEY": "custom_value"})
            )
            config = mgr.load_config(d)
            assert config.get("CUSTOM_KEY") == "custom_value"


# ── DockerBuilder ────────────────────────────────────────────────────────────

class TestDockerBuilder:

    def test_generate_dockerfile(self):
        builder = DockerBuilder()
        with tempfile.TemporaryDirectory() as d:
            path = builder.generate_dockerfile(d)
            assert path.is_file()
            content = path.read_text()
            assert "FROM python:3.12-slim AS builder" in content
            assert "FROM python:3.12-slim AS runtime" in content
            assert "COPY" in content

    def test_generate_compose(self):
        builder = DockerBuilder()
        with tempfile.TemporaryDirectory() as d:
            path = builder.generate_compose(d)
            assert path.is_file()
            content = path.read_text()
            assert "aecos" in content
            assert "services:" in content

    def test_generate_compose_with_ollama(self):
        builder = DockerBuilder()
        with tempfile.TemporaryDirectory() as d:
            path = builder.generate_compose(d, services=["aecos", "ollama"])
            content = path.read_text()
            assert "ollama" in content


# ── CIGenerator ──────────────────────────────────────────────────────────────

class TestCIGenerator:

    def test_generate_github_actions(self):
        generator = CIGenerator()
        with tempfile.TemporaryDirectory() as d:
            path = generator.generate_github_actions(d)
            assert path.is_file()
            assert path.name == "ci.yml"
            content = path.read_text()
            assert "name: AEC OS CI" in content
            assert "3.11" in content
            assert "3.12" in content
            assert "3.13" in content
            assert "pytest" in content


# ── RollbackManager ──────────────────────────────────────────────────────────

class TestRollbackManager:

    def test_create_and_list_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # Init git repo
            subprocess.run(["git", "init"], cwd=root, capture_output=True)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "init"],
                cwd=root, capture_output=True,
                env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                     "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
            )

            mgr = RollbackManager(root)
            meta = mgr.create_snapshot("v0.9")
            assert meta["label"] == "v0.9"
            assert "timestamp" in meta

            snaps = mgr.list_snapshots()
            assert len(snaps) == 1
            assert snaps[0]["label"] == "v0.9"

    def test_rollback_restores_config(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init"], cwd=root, capture_output=True)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "init"],
                cwd=root, capture_output=True,
                env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                     "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
            )

            config_dir = root / ".aecos"
            config_dir.mkdir()
            (config_dir / "config.json").write_text('{"version": "1.0"}')

            mgr = RollbackManager(root)
            mgr.create_snapshot("snap1")

            # Modify config
            (config_dir / "config.json").write_text('{"version": "2.0"}')

            # Rollback
            success = mgr.rollback("snap1")
            assert success is True
            restored = json.loads((config_dir / "config.json").read_text())
            assert restored["version"] == "1.0"
