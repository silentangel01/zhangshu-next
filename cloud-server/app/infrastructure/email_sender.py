"""Email delivery infrastructure for authentication verification codes."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when a verification email cannot be delivered."""


class EmailSender:
    """Send auth verification codes by SMTP or development log delivery."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def send_verification_code(
        self,
        email: str,
        code: str,
        purpose: str,
        expires_minutes: int,
    ) -> None:
        mode = self._settings.email_delivery_mode.lower().strip()
        if mode == "disabled":
            raise EmailDeliveryError("邮件发送未启用。")
        if mode == "log":
            if self._settings.environment == "production":
                raise EmailDeliveryError("生产环境不允许使用日志邮件模式。")
            logger.info(
                "Verification code for %s (%s) is %s, expires in %s minutes.",
                email,
                purpose,
                code,
                expires_minutes,
            )
            return
        if mode != "smtp":
            raise EmailDeliveryError(f"未知邮件发送模式：{mode}")

        self._send_smtp(email, code, purpose, expires_minutes)

    def _send_smtp(
        self,
        email: str,
        code: str,
        purpose: str,
        expires_minutes: int,
    ) -> None:
        settings = self._settings
        if not settings.smtp_host or not settings.smtp_from:
            raise EmailDeliveryError("SMTP_HOST 或 SMTP_FROM 未配置。")

        subject = "章枢注册验证码" if purpose == "register" else "章枢登录验证码"
        action = "注册章枢云账户" if purpose == "register" else "登录章枢云账户"
        body = (
            f"你的章枢验证码是：{code}\n\n"
            f"该验证码用于{action}，{expires_minutes} 分钟内有效。"
            "如果不是你本人操作，请忽略这封邮件。"
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = email
        message.set_content(body)

        try:
            if settings.smtp_use_ssl:
                with smtplib.SMTP_SSL(
                    settings.smtp_host, settings.smtp_port, timeout=10
                ) as server:
                    self._login_if_needed(server)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    settings.smtp_host, settings.smtp_port, timeout=10
                ) as server:
                    if settings.smtp_use_tls:
                        server.starttls()
                    self._login_if_needed(server)
                    server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("验证码邮件发送失败。") from exc

    def _login_if_needed(self, server: smtplib.SMTP) -> None:
        settings = self._settings
        if settings.smtp_username or settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
