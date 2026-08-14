"""Stable device-session lifecycle and sliding refresh coverage."""

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.models.user import utc_now
from tests.conftest import auth_headers, seed_email_verification_code


def test_device_session_survives_rotation_and_logout_revokes_it(client, db_session):
    device_headers = {
        "X-Zhangshu-Device-Id": "desktop-device-1",
        "X-Zhangshu-Device-Name": "%E7%AB%A0%E6%9E%A2%20%C2%B7%20%E6%B5%8B%E8%AF%95%E7%94%B5%E8%84%91",
    }
    code = seed_email_verification_code(client, "device@example.com", "register")
    registered = client.post(
        "/api/auth/register",
        headers=device_headers,
        json={
            "email": "device@example.com",
            "password": "securepassword123",
            "display_name": "Device User",
            "verification_code": code,
        },
    ).json()
    session_id = registered["session_id"]

    listed = client.get(
        "/api/account/sessions",
        headers={**device_headers, **auth_headers(registered["access_token"])},
    )
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["id"] == session_id
    assert listed.json()["sessions"][0]["device_name"] == "章枢 · 测试电脑"
    assert listed.json()["sessions"][0]["is_current"] is True

    rotated = client.post(
        "/api/auth/refresh",
        headers=device_headers,
        json={"refresh_token": registered["refresh_token"]},
    )
    assert rotated.status_code == 200
    assert rotated.json()["session_id"] == session_id

    active = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == session_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    assert active is not None
    assert (active.expires_at - utc_now()).days >= 360

    logout = client.post(
        "/api/auth/logout",
        headers=device_headers,
        json={"refresh_token": rotated.json()["refresh_token"]},
    )
    assert logout.status_code == 200
    assert logout.json()["revoked_count"] == 1

    me = client.get(
        "/api/auth/me",
        headers=auth_headers(rotated.json()["access_token"]),
    )
    assert me.status_code == 401
