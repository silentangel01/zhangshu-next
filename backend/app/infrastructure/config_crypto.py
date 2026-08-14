"""Encryption helpers for sensitive app configuration values.

Derives a Fernet key from platform.node() + getpass.getuser() + a fixed
app-specific salt. The key is never stored — it is re-derived at runtime.
"""

import base64
import getpass
import hashlib
import platform

_APP_SALT = b"zhangshu-app-config-salt-v1"

# Keys whose values must be encrypted before writing to SQLite
SENSITIVE_KEYS: frozenset[str] = frozenset({
    "dashscope_api_key",
    "cloud_access_token",
    "cloud_refresh_token",
    "cloud_user_id",
    "cloud_user_email",
    "cloud_user_phone",
    "cloud_user_oauth_label",
    "cloud_session_id",
    "cloud_device_id",
    "cloud_device_name",
    "cloud_account_snapshot",
})


def _derive_fernet_key() -> bytes:
    """PBKDF2-SHA256 over 'machine:user' with fixed salt, 200k iterations."""
    machine = platform.node() or "unknown-machine"
    user = getpass.getuser() or "unknown-user"
    raw = f"{machine}:{user}".encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", raw, _APP_SALT, iterations=200_000)
    return base64.urlsafe_b64encode(dk[:32])


def _fernet():
    from cryptography.fernet import Fernet

    return Fernet(_derive_fernet_key())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string, returning an ASCII token."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_value(token: str) -> str:
    """Decrypt a token back to plaintext. Raises InvalidToken on mismatch."""
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def is_sensitive(key: str) -> bool:
    """Check whether a config key should be stored encrypted."""
    return key in SENSITIVE_KEYS
