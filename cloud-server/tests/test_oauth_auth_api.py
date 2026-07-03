"""OAuth login API tests with fake provider clients."""

from urllib.parse import parse_qs, urlparse

from app.infrastructure.oauth_clients import OAuthProviderProfile


class FakeOAuthClient:
    def build_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://oauth.example/authorize?state={state}&redirect_uri={redirect_uri}"

    def fetch_profile(self, code: str, redirect_uri: str) -> OAuthProviderProfile:
        assert code == "provider-code"
        assert redirect_uri.endswith("/api/auth/oauth/wechat/callback")
        return OAuthProviderProfile(
            provider="wechat",
            identifier="union-openid-1",
            display_name="微信作者",
            avatar_url=None,
        )


def test_wechat_oauth_start_callback_and_poll(client, monkeypatch):
    monkeypatch.setenv("OAUTH_PUBLIC_BASE_URL", "https://api.zhangshu.xin")
    monkeypatch.setenv("WECHAT_OAUTH_ENABLED", "true")
    monkeypatch.setenv("WECHAT_OAUTH_APP_ID", "wx-test")
    monkeypatch.setenv("WECHAT_OAUTH_APP_SECRET", "secret-test")
    monkeypatch.setattr(
        "app.services.oauth_auth_service.create_oauth_client",
        lambda provider, settings: FakeOAuthClient(),
    )

    start = client.post("/api/auth/oauth/wechat/start")
    assert start.status_code == 200
    start_data = start.json()
    assert start_data["provider"] == "wechat"

    state = parse_qs(urlparse(start_data["authorization_url"]).query)["state"][0]
    callback = client.get(
        "/api/auth/oauth/wechat/callback",
        params={"state": state, "code": "provider-code"},
    )
    assert callback.status_code == 200
    assert "登录已完成" in callback.text

    poll = client.get(
        f"/api/auth/oauth/session/{start_data['session_id']}",
        params={"poll_token": start_data["poll_token"]},
    )
    assert poll.status_code == 200
    poll_data = poll.json()
    assert poll_data["status"] == "completed"
    assert poll_data["access_token"]
    assert poll_data["refresh_token"]
    assert poll_data["display_name"] == "微信作者"


def test_oauth_start_requires_provider_configuration(client):
    response = client.post("/api/auth/oauth/qq/start")

    assert response.status_code == 503
