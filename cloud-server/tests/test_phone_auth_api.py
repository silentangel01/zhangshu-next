"""Phone authentication and identity binding API tests."""

from tests.conftest import (
    auth_headers,
    register_user,
    seed_email_verification_code,
    seed_phone_verification_code,
)


def test_phone_check_available(client):
    response = client.post(
        "/api/auth/phone/check",
        json={"phone_number": "13800138000"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["phone_number"] == "+8613800138000"
    assert data["available"] is True


def test_phone_register_and_profile(client):
    code = seed_phone_verification_code(client, "13800138000", "register")

    response = client.post(
        "/api/auth/register/phone",
        json={
            "phone_number": "13800138000",
            "display_name": "手机用户",
            "verification_code": code,
        },
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    profile = client.get("/api/account/profile", headers=auth_headers(token))
    assert profile.status_code == 200
    data = profile.json()
    assert data["email"] is None
    assert data["phone_number"] == "+8613800138000"
    assert {"provider": "phone", "identifier": "+8613800138000"} in data["identities"]


def test_phone_code_login(client):
    register_code = seed_phone_verification_code(client, "13800138001", "register")
    register_response = client.post(
        "/api/auth/register/phone",
        json={
            "phone_number": "13800138001",
            "display_name": "",
            "verification_code": register_code,
        },
    )
    assert register_response.status_code == 200

    login_code = seed_phone_verification_code(client, "13800138001", "login")
    response = client.post(
        "/api/auth/login/phone-code",
        json={"phone_number": "13800138001", "verification_code": login_code},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_bind_phone_to_email_account(client):
    result = register_user(client, email="bind-phone@example.com")
    token = result["access_token"]
    code = seed_phone_verification_code(client, "13800138002", "bind")

    response = client.post(
        "/api/account/bind/phone",
        headers=auth_headers(token),
        json={"phone_number": "13800138002", "verification_code": code},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "bind-phone@example.com"
    assert data["phone_number"] == "+8613800138002"


def test_bind_email_to_phone_account(client):
    register_code = seed_phone_verification_code(client, "13800138003", "register")
    register_response = client.post(
        "/api/auth/register/phone",
        json={
            "phone_number": "13800138003",
            "display_name": "",
            "verification_code": register_code,
        },
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    email_code = seed_email_verification_code(client, "phone-bind@example.com", "bind")

    response = client.post(
        "/api/account/bind/email",
        headers=auth_headers(token),
        json={"email": "phone-bind@example.com", "verification_code": email_code},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "phone-bind@example.com"
    assert data["phone_number"] == "+8613800138003"
    assert {"provider": "email", "identifier": "phone-bind@example.com"} in data["identities"]


def test_duplicate_phone_identity_rejected(client):
    code = seed_phone_verification_code(client, "13800138004", "register")
    first = client.post(
        "/api/auth/register/phone",
        json={
            "phone_number": "13800138004",
            "display_name": "",
            "verification_code": code,
        },
    )
    assert first.status_code == 200

    result = register_user(client, email="phone-dup@example.com")
    bind_code = seed_phone_verification_code(client, "13800138004", "bind")
    response = client.post(
        "/api/account/bind/phone",
        headers=auth_headers(result["access_token"]),
        json={"phone_number": "13800138004", "verification_code": bind_code},
    )

    assert response.status_code == 400
