"""Tests for backup API endpoints."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


def _create_project(client, token: str) -> str:
    response = client.post(
        "/api/projects",
        json={"title": "备份测试作品"},
        headers=auth_headers(token),
    )
    return response.json()["id"]


def _init_backup(client, token: str, project_id: str, **overrides) -> dict:
    payload = {"filename": "test_backup.zip", "size_bytes": 100}
    payload.update(overrides)
    response = client.post(
        f"/api/projects/{project_id}/backups/init",
        json=payload,
        headers=auth_headers(token),
    )
    return response


class TestInitBackup:
    def test_init_success(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        response = _init_backup(client, result["access_token"], project_id)
        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "upload_id" in data

    def test_init_empty_filename(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        response = _init_backup(
            client, result["access_token"], project_id, filename=""
        )
        assert response.status_code == 400

    def test_init_zero_size(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        response = _init_backup(
            client, result["access_token"], project_id, size_bytes=0
        )
        assert response.status_code == 400

    def test_init_oversize(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        response = _init_backup(
            client, result["access_token"], project_id, size_bytes=999_999_999_999
        )
        assert response.status_code == 400

    def test_init_other_user_project(self, client):
        user_a = register_user(client, email="a@example.com")
        user_b = register_user(client, email="b@example.com")

        project_id = _create_project(client, user_a["access_token"])

        response = _init_backup(client, user_b["access_token"], project_id)
        assert response.status_code == 404


class TestCompleteBackup:
    def test_complete_success(self, client, mock_oss):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        init_resp = _init_backup(client, result["access_token"], project_id)
        upload_id = init_resp.json()["upload_id"]

        # mock_oss.head_object returns size=100, matching init
        response = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={
                "upload_id": upload_id,
                "checksum_sha256": "a" * 64,
            },
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "object_key" in data

    def test_complete_invalid_upload_id(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        response = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={
                "upload_id": "nonexistent-id",
                "checksum_sha256": "a" * 64,
            },
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 404

    def test_complete_invalid_checksum(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        init_resp = _init_backup(client, result["access_token"], project_id)
        upload_id = init_resp.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={"upload_id": upload_id, "checksum_sha256": "not-hex"},
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 400

    def test_complete_size_mismatch(self, client, mock_oss):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])

        init_resp = _init_backup(
            client, result["access_token"], project_id, size_bytes=200
        )
        upload_id = init_resp.json()["upload_id"]

        # mock_oss.head_object returns size=100, but we declared 200
        response = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={"upload_id": upload_id, "checksum_sha256": "b" * 64},
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 400


class TestListBackups:
    def test_list_backups(self, client, mock_oss):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])
        headers = auth_headers(result["access_token"])

        # Init + complete a backup
        init_resp = _init_backup(client, result["access_token"], project_id)
        upload_id = init_resp.json()["upload_id"]
        client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={"upload_id": upload_id, "checksum_sha256": "c" * 64},
            headers=headers,
        )

        response = client.get(
            f"/api/projects/{project_id}/backups", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert "id" in item
        assert "filename" in item
        assert "size_bytes" in item
        assert "status" in item
        assert item["status"] == "success"


class TestDownloadUrl:
    def test_download_success(self, client, mock_oss):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])
        headers = auth_headers(result["access_token"])

        init_resp = _init_backup(client, result["access_token"], project_id)
        upload_id = init_resp.json()["upload_id"]
        complete_resp = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={"upload_id": upload_id, "checksum_sha256": "d" * 64},
            headers=headers,
        )
        backup_id = complete_resp.json()["id"]

        response = client.get(
            f"/api/projects/{project_id}/backups/{backup_id}/download-url",
            headers=headers,
        )
        assert response.status_code == 200
        assert "download_url" in response.json()

    def test_download_pending_backup(self, client):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])
        headers = auth_headers(result["access_token"])

        init_resp = _init_backup(client, result["access_token"], project_id)
        # Don't complete — try to download the uploading backup
        # We need the backup_id, but init doesn't return it directly.
        # List backups to get it.
        list_resp = client.get(
            f"/api/projects/{project_id}/backups", headers=headers
        )
        backup_id = list_resp.json()["items"][0]["id"]

        response = client.get(
            f"/api/projects/{project_id}/backups/{backup_id}/download-url",
            headers=headers,
        )
        assert response.status_code == 400


class TestDeleteBackup:
    def test_delete_success(self, client, mock_oss):
        result = register_user(client)
        project_id = _create_project(client, result["access_token"])
        headers = auth_headers(result["access_token"])

        init_resp = _init_backup(client, result["access_token"], project_id)
        upload_id = init_resp.json()["upload_id"]
        complete_resp = client.post(
            f"/api/projects/{project_id}/backups/complete",
            json={"upload_id": upload_id, "checksum_sha256": "e" * 64},
            headers=headers,
        )
        backup_id = complete_resp.json()["id"]

        response = client.delete(
            f"/api/projects/{project_id}/backups/{backup_id}",
            headers=headers,
        )
        assert response.status_code == 204

        # Should no longer appear in list
        list_resp = client.get(
            f"/api/projects/{project_id}/backups", headers=headers
        )
        assert list_resp.json()["total"] == 0
