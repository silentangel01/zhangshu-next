"""Tests for admin monitoring API — overview and refresh with mocked Aliyun APIs."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, utc_now
from app.services.admin_monitoring_service import AdminMonitoringService
from app.services.token_service import create_admin_access_token
from tests.conftest import auth_headers

MOCK_BILLING = {
    "available_amount": "100.00",
    "currency": "CNY",
    "credit_amount": "50.00",
    "mybank_credit_amount": "30.00",
    "available_cash_amount": "20.00",
}

MOCK_OSS = {
    "storage_bytes": 1024,
    "object_count": 10,
    "standard_storage": 512,
    "ia_storage": 256,
    "archive_storage": 256,
    "bucket_name": "test-bucket",
}

MOCK_SERVER = {
    "info": {
        "name": "test-server",
        "status": "Running",
        "public_ip": "1.2.3.4",
        "spec": "2C4G",
        "os_name": "Ubuntu 22.04",
        "created_at": "2025-01-01T00:00:00",
        "expired_at": "2026-12-31T00:00:00",
        "region_id": "cn-hangzhou",
        "charge_type": "PrePaid",
    },
    "monitor": {
        "cpu_usage": 15.0,
        "memory_usage": 42.0,
        "disk_read_iops": 100,
        "disk_write_iops": 50,
        "net_rx_bps": 1024.0,
        "net_tx_bps": 512.0,
        "timestamp": "2026-05-28T12:00:00+08:00",
        "available": True,
    },
}


def _make_admin(db_session: Session, email: str = "mon-admin@example.com") -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Mon Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


@pytest.fixture(autouse=True)
def _clear_monitoring_cache():
    """Clear the class-level cache before and after each test."""
    AdminMonitoringService._cache.clear()
    yield
    AdminMonitoringService._cache.clear()


class TestAdminMonitoring:
    def test_no_auth_rejected(self, client: TestClient):
        response = client.get("/api/admin/monitoring/overview")
        assert response.status_code == 401

    @patch.object(AdminMonitoringService, "_fetch_server", return_value=MOCK_SERVER)
    @patch.object(AdminMonitoringService, "_fetch_oss", return_value=MOCK_OSS)
    @patch.object(AdminMonitoringService, "_fetch_billing", return_value=MOCK_BILLING)
    def test_get_overview(
        self, mock_billing, mock_oss, mock_server,
        client: TestClient, db_session: Session,
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get("/api/admin/monitoring/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "billing" in data
        assert "oss" in data
        assert "server" in data
        # Each module should have data (not error)
        assert data["billing"]["data"] is not None
        assert data["billing"]["error"] is None
        assert data["oss"]["data"]["storage_bytes"] == 1024

    @patch.object(AdminMonitoringService, "_fetch_server", return_value=MOCK_SERVER)
    @patch.object(AdminMonitoringService, "_fetch_oss", return_value=MOCK_OSS)
    @patch.object(AdminMonitoringService, "_fetch_billing", return_value=MOCK_BILLING)
    def test_refresh_all(
        self, mock_billing, mock_oss, mock_server,
        client: TestClient, db_session: Session,
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.post("/api/admin/monitoring/refresh", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["billing"]["data"] is not None

    @patch.object(AdminMonitoringService, "_fetch_server", return_value=MOCK_SERVER)
    @patch.object(AdminMonitoringService, "_fetch_oss", return_value=MOCK_OSS)
    @patch.object(AdminMonitoringService, "_fetch_billing", return_value=MOCK_BILLING)
    def test_refresh_single_module(
        self, mock_billing, mock_oss, mock_server,
        client: TestClient, db_session: Session,
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.post(
            "/api/admin/monitoring/refresh?module=billing", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["billing"]["data"] is not None
