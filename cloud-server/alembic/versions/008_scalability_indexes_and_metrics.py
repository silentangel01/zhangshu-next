"""scalability indexes, trigram search, and metrics snapshot table

Revision ID: 008_scalability_indexes_and_metrics
Revises: 007_admin_privacy_permissions
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_scalability_indexes_and_metrics"
down_revision: Union[str, None] = "007_admin_privacy_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # ── PostgreSQL-only: pg_trgm extension and trigram GIN indexes ────
    if _is_postgres():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_users_email_trgm "
            "ON users USING gin (email gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_users_display_name_trgm "
            "ON users USING gin (display_name gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_feedback_tickets_title_trgm "
            "ON feedback_tickets USING gin (title gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_feedback_tickets_description_trgm "
            "ON feedback_tickets USING gin (description gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_announcements_title_trgm "
            "ON announcements USING gin (title gin_trgm_ops)"
        )

    # ── Cross-dialect composite indexes (idempotent) ─────────────────
    _indexes = [
        ("ix_user_activity_events_event_created", "user_activity_events", "event_type, created_at"),
        ("ix_user_activity_events_created_user", "user_activity_events", "created_at, user_id"),
        ("ix_cloud_backups_status_deleted_created", "cloud_backups", "status, deleted_at, created_at"),
        ("ix_cloud_backups_project_deleted_status", "cloud_backups", "project_id, deleted_at, status"),
        ("ix_cloud_projects_owner_deleted", "cloud_projects", "owner_id, deleted_at"),
        ("ix_feedback_tickets_status_deleted_created", "feedback_tickets", "status, deleted_at, created_at"),
        ("ix_feedback_tickets_priority_status_deleted", "feedback_tickets", "priority, status, deleted_at"),
        ("ix_audit_logs_event_created", "audit_logs", "event, created_at"),
        ("ix_audit_logs_actor_created", "audit_logs", "actor_user_id, created_at"),
        ("ix_rate_limit_events_scope_key_created", "rate_limit_events", "scope, key, created_at"),
    ]
    for name, table, cols in _indexes:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})")

    # ── admin_metric_snapshots table ─────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_metric_snapshots (
            key VARCHAR(64) PRIMARY KEY,
            payload_json TEXT NOT NULL,
            refreshed_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_metric_snapshots_expires "
        "ON admin_metric_snapshots (expires_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_admin_metric_snapshots_expires", "admin_metric_snapshots")
    op.drop_table("admin_metric_snapshots")
    op.drop_index("ix_rate_limit_events_scope_key_created", "rate_limit_events")
    op.drop_index("ix_audit_logs_actor_created", "audit_logs")
    op.drop_index("ix_audit_logs_event_created", "audit_logs")
    op.drop_index("ix_feedback_tickets_priority_status_deleted", "feedback_tickets")
    op.drop_index("ix_feedback_tickets_status_deleted_created", "feedback_tickets")
    op.drop_index("ix_cloud_projects_owner_deleted", "cloud_projects")
    op.drop_index("ix_cloud_backups_project_deleted_status", "cloud_backups")
    op.drop_index("ix_cloud_backups_status_deleted_created", "cloud_backups")
    op.drop_index("ix_user_activity_events_created_user", "user_activity_events")
    op.drop_index("ix_user_activity_events_event_created", "user_activity_events")

    if _is_postgres():
        op.execute("DROP INDEX IF EXISTS ix_announcements_title_trgm")
        op.execute("DROP INDEX IF EXISTS ix_feedback_tickets_description_trgm")
        op.execute("DROP INDEX IF EXISTS ix_feedback_tickets_title_trgm")
        op.execute("DROP INDEX IF EXISTS ix_users_display_name_trgm")
        op.execute("DROP INDEX IF EXISTS ix_users_email_trgm")
