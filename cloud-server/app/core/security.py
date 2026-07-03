"""Security utilities: password hashing, email normalization, JWT helpers."""

from __future__ import annotations

import hashlib
import re

import bcrypt


_bcrypt_rounds: int = 12


def configure_bcrypt(rounds: int) -> None:
    """Set the bcrypt work factor for password hashing."""
    global _bcrypt_rounds
    _bcrypt_rounds = rounds


def normalize_email(email: str) -> str:
    """Trim whitespace and lowercase the email address."""
    return email.strip().lower()


def normalize_phone_number(phone: str) -> str:
    """Normalize a mainland China mobile number to +86 format."""
    digits = re.sub(r"\D", "", phone.strip())
    if digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    if not re.fullmatch(r"1[3-9]\d{9}", digits):
        raise ValueError("请输入有效的中国大陆手机号。")
    return f"+86{digits}"


def mask_phone_number(phone: str) -> str:
    """Mask a normalized phone number for display."""
    try:
        normalized = normalize_phone_number(phone)
    except ValueError:
        return phone
    digits = normalized[3:]
    return f"{digits[:3]}****{digits[-4:]}"


def is_internal_phone_email(email: str) -> bool:
    """Return whether an email is an internal placeholder for phone-only users."""
    return email.endswith("@phone.zhangshu.local")


def is_internal_auth_email(email: str) -> bool:
    """Return whether an email is an internal placeholder for non-email users."""
    return email.endswith("@phone.zhangshu.local") or email.endswith("@oauth.zhangshu.local")


def build_internal_phone_email(phone_number: str) -> str:
    """Build a stable internal placeholder email for phone-only users."""
    digest = sha256_text(normalize_phone_number(phone_number))[:24]
    return f"phone+{digest}@phone.zhangshu.local"


def build_internal_oauth_email(provider: str, identifier: str) -> str:
    """Build a stable internal placeholder email for OAuth-only users."""
    safe_provider = re.sub(r"[^a-z0-9_]", "", provider.lower()) or "oauth"
    digest = sha256_text(f"{safe_provider}:{identifier}")[:24]
    return f"oauth+{safe_provider}+{digest}@oauth.zhangshu.local"


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password is invalid, or None if OK."""
    stripped = password.strip()
    if not stripped:
        return "密码不能为空。"
    if len(stripped) < 10:
        return "密码长度不得少于 10 个字符。"
    encoded = stripped.encode("utf-8")
    if len(encoded) > 72:
        return "密码过长，UTF-8 编码后不得超过 72 字节。"
    return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=_bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_valid_sha256_hex(value: str) -> bool:
    """Check if a string is a valid 64-character hex SHA-256 digest."""
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))
