"""Regression tests for instant local account snapshots."""

from app.services.cloud_account_snapshot_service import CloudAccountSnapshotService


class MemoryConfig:
    def __init__(self):
        self.values: dict[str, str] = {}

    def get_decrypted(self, key: str):
        return self.values.get(key)

    def set_value(self, key: str, value: str):
        self.values[key] = value


class FakeDevice:
    def get_or_create(self):
        return "device-1", "章枢 · 测试电脑"


class FakeAuth:
    def __init__(self):
        self.profile_calls = 0

    def get_account_status(self):
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": "writer@example.com",
            "display_name": "作者",
            "phone_number": None,
            "token_expired": False,
        }

    def get_account_profile(self):
        self.profile_calls += 1
        return {"id": "u1", "display_name": "作者"}

    def get_usage(self):
        return {"storage_used_bytes": 12, "storage_quota_bytes": 1024}


def make_service():
    service = object.__new__(CloudAccountSnapshotService)
    service._config = MemoryConfig()
    service._auth = FakeAuth()
    service._device = FakeDevice()
    return service


def test_get_snapshot_never_contacts_cloud():
    service = make_service()

    snapshot = service.get_snapshot()

    assert snapshot["status"]["logged_in"] is True
    assert snapshot["profile"] is None
    assert snapshot["device"]["id"] == "device-1"
    assert service._auth.profile_calls == 0


def test_refresh_persists_last_good_profile_and_usage():
    service = make_service()

    refreshed = service.refresh_snapshot()
    cached = service.get_snapshot()

    assert refreshed["cache_state"] == "fresh"
    assert cached["profile"]["display_name"] == "作者"
    assert cached["usage"]["storage_used_bytes"] == 12
    assert cached["cached_at"]
