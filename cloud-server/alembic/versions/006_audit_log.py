"""audit log table

Revision ID: 006_audit_log
Revises: 005_feedback_replies
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_audit_log"
down_revision: Union[str, None] = "005_feedback_replies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event",
            sa.String(64),
            nullable=False,
            comment="Event type: login_success, backup_init, admin_toggle_active, ...",
        ),
        sa.Column("request_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("client_ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("backup_id", sa.String(36), nullable=False, server_default=""),
        sa.Column(
            "result",
            sa.String(16),
            nullable=False,
            server_default="success",
            comment="success | failure | error",
        ),
        sa.Column(
            "reason_code",
            sa.String(32),
            nullable=False,
            server_default="",
            comment="Machine-readable failure reason",
        ),
        sa.Column(
            "extra_json",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded non-sensitive extra fields",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_event", "audit_logs", ["event"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index(
        "ix_audit_logs_event_created",
        "audit_logs",
        ["event", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_event_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event", table_name="audit_logs")
    op.drop_table("audit_logs")
