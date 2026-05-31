"""Privacy redaction utilities — email, IP, user-agent masking and hashing.

These functions ensure that sensitive data is never stored or displayed in
raw form unless explicitly required by the security policy.
"""

from __future__ import annotations

import hashlib


def mask_email(email: str) -> str:
    """Mask an email for display: ``john@example.com`` → ``j***@example.com``."""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    local, domain = parts
    if len(local) <= 1:
        masked_local = "***"
    else:
        masked_local = local[0] + "***"
    return f"{masked_local}@{domain}"


def mask_ip(ip: str) -> str:
    """Mask an IP address for display.

    IPv4: ``192.168.1.42`` → ``192.168.1.xxx``
    IPv6: ``2001:db8::1`` → ``2001:xxxx``
    Empty or invalid: ``***``
    """
    if not ip:
        return "***"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    if ":" in ip:
        first = ip.split(":")[0]
        return f"{first}:xxxx"
    return "***"


def hash_ip(ip: str) -> str:
    """Produce a non-reversible SHA-256 hash of an IP for correlation.

    Returns empty string for empty input.
    """
    if not ip:
        return ""
    return hashlib.sha256(ip.strip().encode()).hexdigest()[:16]


def safe_user_agent(ua: str, max_len: int = 200) -> str:
    """Truncate and sanitize a user-agent string for storage."""
    if not ua:
        return ""
    ua = ua.strip()
    if len(ua) > max_len:
        ua = ua[:max_len] + "..."
    return ua


def sanitize_filename(filename: str) -> str:
    """Remove path separators and null bytes from a filename."""
    if not filename:
        return ""
    filename = filename.replace("\\", "/").split("/")[-1]
    filename = filename.replace("\x00", "")
    return filename or "unnamed"
