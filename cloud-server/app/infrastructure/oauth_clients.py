"""OAuth provider clients for WeChat and QQ login."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.core.config import Settings


class OAuthProviderError(Exception):
    """Raised when an OAuth provider rejects or cannot complete the flow."""


@dataclass(frozen=True)
class OAuthProviderProfile:
    provider: str
    identifier: str
    display_name: str
    avatar_url: str | None = None


class OAuthProviderClient:
    def build_authorization_url(self, state: str, redirect_uri: str) -> str:
        raise NotImplementedError

    def fetch_profile(self, code: str, redirect_uri: str) -> OAuthProviderProfile:
        raise NotImplementedError


def create_oauth_client(provider: str, settings: Settings) -> OAuthProviderClient:
    if provider == "wechat":
        return WeChatOAuthClient(settings)
    if provider == "qq":
        return QQOAuthClient(settings)
    raise OAuthProviderError("不支持的登录方式。")


def _http_get_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
    except OSError as exc:
        raise OAuthProviderError("无法连接第三方登录服务。") from exc

    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise OAuthProviderError("第三方登录服务返回异常。") from exc
    if not isinstance(data, dict):
        raise OAuthProviderError("第三方登录服务返回异常。")
    return data


class WeChatOAuthClient(OAuthProviderClient):
    def __init__(self, settings: Settings):
        self._app_id = settings.wechat_oauth_app_id
        self._app_secret = settings.wechat_oauth_app_secret

    def build_authorization_url(self, state: str, redirect_uri: str) -> str:
        query = urllib.parse.urlencode(
            {
                "appid": self._app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "snsapi_login",
                "state": state,
            }
        )
        return f"https://open.weixin.qq.com/connect/qrconnect?{query}#wechat_redirect"

    def fetch_profile(self, code: str, redirect_uri: str) -> OAuthProviderProfile:
        token_query = urllib.parse.urlencode(
            {
                "appid": self._app_id,
                "secret": self._app_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        )
        token = _http_get_json(
            f"https://api.weixin.qq.com/sns/oauth2/access_token?{token_query}"
        )
        if token.get("errcode"):
            raise OAuthProviderError(str(token.get("errmsg") or "微信登录失败。"))

        access_token = str(token.get("access_token") or "")
        openid = str(token.get("openid") or "")
        if not access_token or not openid:
            raise OAuthProviderError("微信登录授权信息不完整。")

        user_query = urllib.parse.urlencode(
            {"access_token": access_token, "openid": openid, "lang": "zh_CN"}
        )
        user = _http_get_json(f"https://api.weixin.qq.com/sns/userinfo?{user_query}")
        if user.get("errcode"):
            raise OAuthProviderError(str(user.get("errmsg") or "微信登录失败。"))

        identifier = str(user.get("unionid") or token.get("unionid") or openid)
        nickname = str(user.get("nickname") or "微信用户")
        avatar = user.get("headimgurl")
        return OAuthProviderProfile(
            provider="wechat",
            identifier=identifier,
            display_name=nickname[:128],
            avatar_url=avatar if isinstance(avatar, str) else None,
        )


class QQOAuthClient(OAuthProviderClient):
    def __init__(self, settings: Settings):
        self._app_id = settings.qq_oauth_app_id
        self._app_secret = settings.qq_oauth_app_secret

    def build_authorization_url(self, state: str, redirect_uri: str) -> str:
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self._app_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": "get_user_info",
            }
        )
        return f"https://graph.qq.com/oauth2.0/authorize?{query}"

    def fetch_profile(self, code: str, redirect_uri: str) -> OAuthProviderProfile:
        token_query = urllib.parse.urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": self._app_id,
                "client_secret": self._app_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "fmt": "json",
            }
        )
        token = _http_get_json(f"https://graph.qq.com/oauth2.0/token?{token_query}")
        if token.get("error"):
            raise OAuthProviderError(str(token.get("error_description") or "QQ 登录失败。"))

        access_token = str(token.get("access_token") or "")
        if not access_token:
            raise OAuthProviderError("QQ 登录授权信息不完整。")

        openid_query = urllib.parse.urlencode({"access_token": access_token, "fmt": "json"})
        openid_payload = _http_get_json(f"https://graph.qq.com/oauth2.0/me?{openid_query}")
        openid = str(openid_payload.get("openid") or "")
        if not openid:
            raise OAuthProviderError("QQ 登录授权信息不完整。")

        user_query = urllib.parse.urlencode(
            {
                "access_token": access_token,
                "oauth_consumer_key": self._app_id,
                "openid": openid,
            }
        )
        user = _http_get_json(f"https://graph.qq.com/user/get_user_info?{user_query}")
        if int(user.get("ret") or 0) != 0:
            raise OAuthProviderError(str(user.get("msg") or "QQ 登录失败。"))

        nickname = str(user.get("nickname") or "QQ 用户")
        avatar = user.get("figureurl_qq_2") or user.get("figureurl_qq_1")
        return OAuthProviderProfile(
            provider="qq",
            identifier=openid,
            display_name=nickname[:128],
            avatar_url=avatar if isinstance(avatar, str) else None,
        )
