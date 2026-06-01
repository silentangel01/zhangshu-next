"""admin role and privacy fields

Revision ID: 007_admin_privacy_permissions
Revises: 006_audit_log
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_admin_privacy_permissions"
down_revision: Union[str, None] = "006_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add admin_role to users table
    op.add_column(
        "users",
        sa.Column(
            "admin_role",
            sa.String(32),
            nullable=True,
            comment="owner | admin | support | ops | readonly",
        ),
    )
    op.create_index("ix_users_admin_role", "users", ["admin_role"])

    # Back-fill existing is_admin users as "owner"
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("UPDATE users SET admin_role = 'owner' WHERE is_admin = true")
    else:
        op.execute("UPDATE users SET admin_role = 'owner' WHERE is_admin = 1")

    # Add privacy-enhanced fields to audit_logs
    op.add_column(
        "audit_logs",
        sa.Column("actor_user_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("target_user_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("client_ip_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("client_ip_masked", sa.String(45), nullable=True),
    )
    op.create_index(
        "ix_audit_logs_actor", "audit_logs", ["actor_user_id"]
    )
    op.create_index(
        "ix_audit_logs_target", "audit_logs", ["target_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor", table_name="audit_logs")
    op.drop_column("audit_logs", "client_ip_masked")
    op.drop_column("audit_logs", "client_ip_hash")
    op.drop_column("audit_logs", "target_user_id")
    op.drop_column("audit_logs", "actor_user_id")
    op.drop_index("ix_users_admin_role", table_name="users")
    op.drop_column("users", "admin_role")
