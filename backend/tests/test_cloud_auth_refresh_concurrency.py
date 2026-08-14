"""A rotated refresh token may be consumed only once per process."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.services.cloud_auth_service import CloudAuthService


class FakeDb:
    def expire_all(self):
        pass


class SharedConfig:
    def __init__(self):
        self.values = {
            "cloud_access_token": "old-access",
            "cloud_refresh_token": "old-refresh",
            "cloud_user_id": "u1",
            "cloud_user_email": "writer@example.com",
        }
        self.lock = threading.Lock()

    def get_decrypted(self, key):
        with self.lock:
            return self.values.get(key)

    def apply_atomic(self, values, *, delete_keys=None):
        with self.lock:
            self.values.update(values)
            for key in delete_keys or set():
                self.values.pop(key, None)


class RefreshClient:
    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    def refresh(self, token):
        with self.lock:
            self.calls += 1
        assert token == "old-refresh"
        time.sleep(0.05)
        return {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "user_id": "u1",
            "session_id": "session-1",
        }


def test_concurrent_401s_share_one_refresh(monkeypatch):
    config = SharedConfig()
    client = RefreshClient()

    def build_service():
        service = object.__new__(CloudAuthService)
        service._db = FakeDb()
        service._config = config
        return service

    monkeypatch.setattr(
        CloudAuthService,
        "_build_client",
        lambda self, **kwargs: client,
    )
    first = build_service()
    second = build_service()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda service: service._try_refresh_token("old-access"),
            (first, second),
        ))

    assert results == [True, True]
    assert client.calls == 1
    assert config.values["cloud_access_token"] == "new-access"
    assert config.values["cloud_refresh_token"] == "new-refresh"
