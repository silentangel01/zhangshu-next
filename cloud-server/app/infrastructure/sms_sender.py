"""SMS delivery infrastructure for phone verification codes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SmsDeliveryError(Exception):
    """Raised when a phone verification code cannot be delivered."""


class SmsSender:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def send_verification_code(
        self,
        phone_number: str,
        code: str,
        purpose: str,
        expires_minutes: int,
    ) -> None:
        mode = self._settings.sms_delivery_mode.lower().strip()
        if mode == "disabled":
            raise SmsDeliveryError("短信发送未启用。")
        if mode == "log":
            if self._settings.environment == "production":
                raise SmsDeliveryError("生产环境不允许使用日志短信模式。")
            logger.info(
                "Phone verification code for %s (%s) is %s, expires in %s minutes.",
                phone_number,
                purpose,
                code,
                expires_minutes,
            )
            return
        if mode != "aliyun":
            raise SmsDeliveryError(f"未知短信发送模式：{mode}")
        self._send_aliyun(phone_number, code)

    def _send_aliyun(self, phone_number: str, code: str) -> None:
        settings = self._settings
        required = (
            settings.aliyun_sms_access_key_id,
            settings.aliyun_sms_access_key_secret,
            settings.aliyun_sms_sign_name,
            settings.aliyun_sms_template_code,
        )
        if not all(required):
            raise SmsDeliveryError("阿里云短信配置不完整。")

        phone_for_api = phone_number
        if phone_for_api.startswith("+86"):
            phone_for_api = phone_for_api[3:]

        params = {
            "AccessKeyId": settings.aliyun_sms_access_key_id,
            "Action": "SendSms",
            "Format": "JSON",
            "PhoneNumbers": phone_for_api,
            "RegionId": settings.aliyun_sms_region_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid4()),
            "SignatureVersion": "1.0",
            "SignName": settings.aliyun_sms_sign_name,
            "TemplateCode": settings.aliyun_sms_template_code,
            "TemplateParam": json.dumps({"code": code}, separators=(",", ":")),
            "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Version": "2017-05-25",
        }
        params["Signature"] = self._sign(params, settings.aliyun_sms_access_key_secret)
        url = settings.aliyun_sms_endpoint.rstrip("/") + "/?" + urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise SmsDeliveryError("验证码短信发送失败。") from exc

        if payload.get("Code") != "OK":
            logger.warning("Aliyun SMS failed: %s", payload)
            raise SmsDeliveryError(payload.get("Message") or "验证码短信发送失败。")

    @staticmethod
    def _percent_encode(value: str) -> str:
        return urllib.parse.quote(value, safe="~")

    @classmethod
    def _sign(cls, params: dict[str, str], secret: str) -> str:
        canonical = "&".join(
            f"{cls._percent_encode(k)}={cls._percent_encode(str(params[k]))}"
            for k in sorted(params)
        )
        string_to_sign = "GET&%2F&" + cls._percent_encode(canonical)
        digest = hmac.new(
            (secret + "&").encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")
