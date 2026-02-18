"""Tests for Item 17 — Security & Audit."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from aecos.security.audit import AuditEntry, AuditLogger
from aecos.security.encryption import EncryptionManager, XORProvider
from aecos.security.hasher import Hasher
from aecos.security.policies import SecurityPolicy
from aecos.security.rbac import check_permission, require_role
from aecos.security.report import Finding, SecurityReport
from aecos.security.scanner import SecurityScanner


# ── AuditLogger ──────────────────────────────────────────────────────────────

class TestAuditLogger:

    def test_log_creates_entry(self):
        logger = AuditLogger(":memory:")
        entry = logger.log("alice", "create", "wall_001")
        assert isinstance(entry, AuditEntry)
        assert entry.user == "alice"
        assert entry.action == "create"
        assert entry.resource == "wall_001"
        assert entry.entry_hash != ""
        assert entry.prev_entry_hash == ""
        logger.close()

    def test_hash_chain_valid_after_10_events(self):
        logger = AuditLogger(":memory:")
        for i in range(10):
            logger.log(f"user_{i}", f"action_{i}", f"resource_{i}")
        assert logger.verify_chain() is True
        logger.close()

    def test_hash_chain_detects_tampering(self):
        logger = AuditLogger(":memory:")
        for i in range(10):
            logger.log(f"user_{i}", f"action_{i}", f"resource_{i}")

        # Tamper with a middle entry
        logger._conn.execute(
            "UPDATE audit_log SET action = 'TAMPERED' WHERE id = 5"
        )
        logger._conn.commit()

        assert logger.verify_chain() is False
        logger.close()

    def test_get_log_filters(self):
        logger = AuditLogger(":memory:")
        logger.log("alice", "create", "wall_001")
        logger.log("bob", "modify", "wall_002")
        logger.log("alice", "delete", "wall_001")

        alice_log = logger.get_log(user="alice")
        assert len(alice_log) == 2

        create_log = logger.get_log(action="create")
        assert len(create_log) == 1

        resource_log = logger.get_log(resource="wall_002")
        assert len(resource_log) == 1
        logger.close()

    def test_export_log_json(self):
        logger = AuditLogger(":memory:")
        logger.log("alice", "create", "wall_001")
        exported = logger.export_log(format="json")
        data = json.loads(exported)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["user"] == "alice"
        logger.close()

    def test_hash_chain_links_entries(self):
        logger = AuditLogger(":memory:")
        e1 = logger.log("alice", "create", "wall_001")
        e2 = logger.log("bob", "modify", "wall_002")
        assert e2.prev_entry_hash == e1.entry_hash
        logger.close()

    def test_before_after_hash_stored(self):
        logger = AuditLogger(":memory:")
        entry = logger.log(
            "alice", "create", "wall_001",
            before_hash="aaa", after_hash="bbb"
        )
        assert entry.before_hash == "aaa"
        assert entry.after_hash == "bbb"
        logger.close()


# ── Hasher ───────────────────────────────────────────────────────────────────

class TestHasher:

    def test_hash_string(self):
        h1 = Hasher.hash_string("hello")
        h2 = Hasher.hash_string("hello")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_hash_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            h1 = Hasher.hash_file(f.name)
            h2 = Hasher.hash_file(f.name)
        assert h1 == h2
        assert len(h1) == 64
        os.unlink(f.name)

    def test_hash_folder(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("aaa")
            (Path(d) / "b.txt").write_text("bbb")
            h1 = Hasher.hash_folder(d)
            h2 = Hasher.hash_folder(d)
        assert h1 == h2
        assert len(h1) == 64


# ── Encryption ───────────────────────────────────────────────────────────────

class TestEncryption:

    def test_xor_round_trip(self):
        provider = XORProvider()
        key = provider.generate_key()
        data = b"Hello, AEC OS!"
        encrypted = provider.encrypt(data, key)
        decrypted = provider.decrypt(encrypted, key)
        assert decrypted == data
        assert encrypted != data

    def test_encrypt_decrypt_file(self):
        mgr = EncryptionManager(provider=XORProvider())
        key = mgr.generate_key()

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as f:
            original = b'{"element": "wall_001"}'
            f.write(original)
            f.flush()

            mgr.encrypt_file(f.name, key)
            assert Path(f.name).read_bytes() != original

            mgr.decrypt_file(f.name, key)
            assert Path(f.name).read_bytes() == original

        os.unlink(f.name)

    def test_encrypt_folder(self):
        mgr = EncryptionManager(provider=XORProvider())
        key = mgr.generate_key()

        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.json").write_text('{"a":1}')
            (Path(d) / "b.txt").write_text("not encrypted")
            (Path(d) / "c.ifc").write_text("ifc data")

            encrypted = mgr.encrypt_folder(d, key, patterns=[".json", ".ifc"])
            assert len(encrypted) == 2

            # b.txt should be unchanged
            assert (Path(d) / "b.txt").read_text() == "not encrypted"

    def test_xor_fallback_without_cryptography(self):
        """XOR provider works when cryptography is unavailable."""
        mgr = EncryptionManager(provider=XORProvider())
        key = mgr.generate_key()
        data = b"test data"
        enc = mgr.provider.encrypt(data, key)
        dec = mgr.provider.decrypt(enc, key)
        assert dec == data

    def test_key_store_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            mgr = EncryptionManager(project_root=d, provider=XORProvider())
            key = mgr.generate_key()
            mgr.store_key("test_key", key)
            loaded = mgr.load_key("test_key")
            assert loaded == key


# ── RBAC ─────────────────────────────────────────────────────────────────────

class TestRBAC:

    def test_check_permission_admin(self):
        assert check_permission("alice", "admin", "create") is True
        assert check_permission("alice", "admin", "audit_export") is True
        assert check_permission("alice", "admin", "key_manage") is True

    def test_check_permission_designer(self):
        assert check_permission("bob", "designer", "create") is True
        assert check_permission("bob", "designer", "modify") is True
        assert check_permission("bob", "designer", "delete") is False

    def test_check_permission_reviewer(self):
        assert check_permission("carol", "reviewer", "read") is True
        assert check_permission("carol", "reviewer", "approve") is True
        assert check_permission("carol", "reviewer", "create") is False
        assert check_permission("carol", "reviewer", "modify") is False

    def test_check_permission_viewer(self):
        assert check_permission("dave", "viewer", "read") is True
        assert check_permission("dave", "viewer", "pull") is True
        assert check_permission("dave", "viewer", "modify") is False
        assert check_permission("dave", "viewer", "create") is False

    def test_check_permission_auditor(self):
        assert check_permission("eve", "auditor", "read") is True
        assert check_permission("eve", "auditor", "audit_export") is True
        assert check_permission("eve", "auditor", "modify") is False

    def test_require_role_decorator(self):
        @require_role("admin", "designer")
        def create_element(user, role):
            return "created"

        assert create_element("alice", role="admin") == "created"
        assert create_element("bob", role="designer") == "created"

        with pytest.raises(PermissionError):
            create_element("carol", role="viewer")


# ── SecurityScanner ──────────────────────────────────────────────────────────

class TestSecurityScanner:

    def test_scan_secrets_detects_api_key(self):
        scanner = SecurityScanner()
        with tempfile.TemporaryDirectory() as d:
            # Plant a fake API key
            (Path(d) / "config.json").write_text(
                '{"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz1234"}'
            )
            findings = scanner.scan_secrets(d)
            assert len(findings) >= 1
            assert findings[0].severity == "high"
            assert findings[0].category == "secret"

    def test_scan_secrets_clean(self):
        scanner = SecurityScanner()
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "safe.json").write_text('{"name": "wall"}')
            findings = scanner.scan_secrets(d)
            assert len(findings) == 0

    def test_scan_audit_integrity_no_logger(self):
        scanner = SecurityScanner(audit_logger=None)
        findings = scanner.scan_audit_integrity()
        assert len(findings) == 1
        assert findings[0].severity == "info"

    def test_scan_audit_integrity_valid_chain(self):
        logger = AuditLogger(":memory:")
        for i in range(5):
            logger.log(f"user_{i}", f"action_{i}")
        scanner = SecurityScanner(audit_logger=logger)
        findings = scanner.scan_audit_integrity()
        # Should have an "info" finding saying chain is valid
        info = [f for f in findings if f.category == "audit" and "verified" in f.message]
        assert len(info) == 1

    def test_scan_all(self):
        scanner = SecurityScanner(audit_logger=AuditLogger(":memory:"))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "safe.json").write_text('{"name": "wall"}')
            report = scanner.scan_all(d)
            assert isinstance(report, SecurityReport)
            assert report.chain_valid is True


# ── SecurityReport ───────────────────────────────────────────────────────────

class TestSecurityReport:

    def test_to_markdown(self):
        report = SecurityReport(
            findings=[
                Finding(severity="high", category="secret", message="Found API key", file_path="config.json"),
                Finding(severity="low", category="permission", message="Minor issue"),
            ],
            chain_valid=True,
            overall_status="warning",
        )
        md = report.to_markdown()
        assert "# Security Report" in md
        assert "HIGH" in md
        assert "Found API key" in md
        assert "config.json" in md

    def test_to_json(self):
        report = SecurityReport(findings=[], chain_valid=True, overall_status="clean")
        data = json.loads(report.to_json())
        assert data["overall_status"] == "clean"
        assert data["chain_valid"] is True


# ── SecurityPolicy ───────────────────────────────────────────────────────────

class TestSecurityPolicy:

    def test_default_policy(self):
        policy = SecurityPolicy()
        assert policy.max_failed_logins == 5
        assert "admin" in policy.role_permissions
        assert "viewer" in policy.role_permissions
        assert "auditor" in policy.role_permissions
