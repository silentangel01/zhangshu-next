"""Admin role-based permission matrix.

Defines roles and their associated permission sets. All permission checks
go through this module — individual routers should never duplicate role logic.

Compatibility: existing ``is_admin`` / ``ADMIN_EMAILS`` bootstrap maps to
the ``owner`` role so current administrators retain full access after migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.models.user import User


# ── Roles ────────────────────────────────────────────────────────────────

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_SUPPORT = "support"
ROLE_OPS = "ops"
ROLE_READONLY = "readonly"

ALL_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_SUPPORT, ROLE_OPS, ROLE_READONLY)


# ── Permission constants ─────────────────────────────────────────────────

DASHBOARD_VIEW = "dashboard:view"
FEEDBACK_VIEW = "feedback:view"
FEEDBACK_REPLY = "feedback:reply"
FEEDBACK_MANAGE = "feedback:manage"
FEEDBACK_ATTACHMENT_DOWNLOAD = "feedback:attachment_download"
USERS_VIEW = "users:view"
USERS_SENSITIVE_VIEW = "users:sensitive_view"
USERS_TOGGLE_ACTIVE = "users:toggle_active"
USERS_FORCE_LOGOUT = "users:force_logout"
ADMIN_ROLES_MANAGE = "admin_roles:manage"
ANNOUNCEMENTS_VIEW = "announcements:view"
ANNOUNCEMENTS_WRITE = "announcements:write"
ANNOUNCEMENTS_PUBLISH = "announcements:publish"
ANNOUNCEMENTS_DELETE = "announcements:delete"
AUDIT_VIEW = "audit:view"
MONITORING_VIEW = "monitoring:view"
SEARCH_GLOBAL = "search:global"

ALL_PERMISSIONS = (
    DASHBOARD_VIEW,
    FEEDBACK_VIEW,
    FEEDBACK_REPLY,
    FEEDBACK_MANAGE,
    FEEDBACK_ATTACHMENT_DOWNLOAD,
    USERS_VIEW,
    USERS_SENSITIVE_VIEW,
    USERS_TOGGLE_ACTIVE,
    USERS_FORCE_LOGOUT,
    ADMIN_ROLES_MANAGE,
    ANNOUNCEMENTS_VIEW,
    ANNOUNCEMENTS_WRITE,
    ANNOUNCEMENTS_PUBLISH,
    ANNOUNCEMENTS_DELETE,
    AUDIT_VIEW,
    MONITORING_VIEW,
    SEARCH_GLOBAL,
)


# ── Role → Permission matrix ─────────────────────────────────────────────

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_OWNER: frozenset(ALL_PERMISSIONS),

    ROLE_ADMIN: frozenset({
        DASHBOARD_VIEW,
        FEEDBACK_VIEW,
        FEEDBACK_REPLY,
        FEEDBACK_MANAGE,
        FEEDBACK_ATTACHMENT_DOWNLOAD,
        USERS_VIEW,
        USERS_SENSITIVE_VIEW,
        USERS_TOGGLE_ACTIVE,
        USERS_FORCE_LOGOUT,
        ANNOUNCEMENTS_VIEW,
        ANNOUNCEMENTS_WRITE,
        ANNOUNCEMENTS_PUBLISH,
        ANNOUNCEMENTS_DELETE,
        AUDIT_VIEW,
        MONITORING_VIEW,
        SEARCH_GLOBAL,
    }),

    ROLE_SUPPORT: frozenset({
        DASHBOARD_VIEW,
        FEEDBACK_VIEW,
        FEEDBACK_REPLY,
        USERS_VIEW,
        ANNOUNCEMENTS_VIEW,
        SEARCH_GLOBAL,
    }),

    ROLE_OPS: frozenset({
        DASHBOARD_VIEW,
        MONITORING_VIEW,
        AUDIT_VIEW,
        ANNOUNCEMENTS_VIEW,
    }),

    ROLE_READONLY: frozenset({
        DASHBOARD_VIEW,
        FEEDBACK_VIEW,
        USERS_VIEW,
        ANNOUNCEMENTS_VIEW,
    }),
}


# ── Public API ───────────────────────────────────────────────────────────

def effective_admin_role(user: User, settings: Settings) -> str | None:
    """Determine the effective admin role for a user.

    Priority:
    1. ``user.admin_role`` if set.
    2. ``user.is_admin`` or email in ``ADMIN_EMAILS`` → ``owner`` (bootstrap).
    3. ``None`` if the user has no admin privileges at all.
    """
    if user.admin_role and user.admin_role in ALL_ROLES:
        return user.admin_role

    if user.is_admin or user.email.lower() in settings.admin_email_list:
        return ROLE_OWNER

    return None


def permissions_for_role(role: str | None) -> frozenset[str]:
    """Return the permission set for a given role. Unknown roles get nothing."""
    if role is None:
        return frozenset()
    return _ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(user: User, permission: str, settings: Settings) -> bool:
    """Check whether a user holds a specific permission."""
    role = effective_admin_role(user, settings)
    return permission in permissions_for_role(role)


def get_permission_matrix() -> dict[str, list[str]]:
    """Return the full role → permissions mapping (for the admin API)."""
    return {
        role: sorted(perms)
        for role, perms in _ROLE_PERMISSIONS.items()
    }
