"""Tests for audit logging."""

from __future__ import annotations

import logging

from app.core.audit import audit_event


class TestAuditEvent:
    def test_basic_audit_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            audit_event(
                "login_success",
                request_id="req123",
                client_ip="10.0.0.1",
                user_id="user-abc",
            )
        assert any("login_success" in r.message for r in caplog.records)
        assert any("user-abc" in r.message for r in caplog.records)

    def test_audit_event_with_failure(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            audit_event(
                "login_failed",
                request_id="req456",
                client_ip="10.0.0.2",
                result="failure",
                reason_code="401",
            )
        assert any("login_failed" in r.message for r in caplog.records)
        assert any("failure" in r.message for r in caplog.records)

    def test_audit_event_backup(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            audit_event(
                "backup_init",
                request_id="req789",
                client_ip="10.0.0.3",
                user_id="user-xyz",
                project_id="proj-123",
                extra={"file_name": "backup.zip", "size_bytes": 1024},
            )
        assert any("backup_init" in r.message for r in caplog.records)
        record = [r for r in caplog.records if "backup_init" in r.message][0]
        assert getattr(record, "audit_file_name", None) == "backup.zip"
        assert getattr(record, "audit_size_bytes", None) == 1024

    def test_audit_event_ignores_unknown_extra(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            audit_event(
                "test_event",
                extra={"secret_token": "should_be_ignored", "file_name": "ok.txt"},
            )
        record = [r for r in caplog.records if "test_event" in r.message][0]
        assert not hasattr(record, "audit_secret_token")
        assert getattr(record, "audit_file_name", None) == "ok.txt"

    def test_audit_event_empty_user(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            audit_event("login_failed", client_ip="10.0.0.1")
        assert any("anonymous" in r.message for r in caplog.records)


class TestAuditIntegration:
    def test_register_emits_audit(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            client.post(
                "/api/auth/register",
                json={
                    "email": "audit@example.com",
                    "password": "securepassword123",
                    "display_name": "Audit",
                },
            )
        assert any("user_registered" in r.message for r in caplog.records)

    def test_login_failure_emits_audit(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="app.audit"):
            client.post(
                "/api/auth/login",
                json={"email": "nonexist@example.com", "password": "wrongpass123"},
            )
        assert any("login_failed" in r.message for r in caplog.records)
