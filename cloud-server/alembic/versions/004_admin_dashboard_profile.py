"""admin dashboard, profile, activity events

Revision ID: 004_admin_dashboard_profile
Revises: 003_announcements_feedback
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_admin_dashboard_profile"
down_revision: Union[str, None] = "003_announcements_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: profile + activity fields ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("avatar_object_key", sa.String(512), nullable=True)
        )
        batch_op.add_column(
            sa.Column("avatar_content_type", sa.String(80), nullable=True)
        )
        batch_op.add_column(
            sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("signature", sa.String(160), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "login_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    # --- user_activity_events ---
    op.create_table(
        "user_activity_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("client_ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_user_activity_user_id", "user_activity_events", ["user_id"]
    )
    op.create_index(
        "ix_user_activity_event_type", "user_activity_events", ["event_type"]
    )
    op.create_index(
        "ix_user_activity_created_at", "user_activity_events", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_activity_created_at", table_name="user_activity_events")
    op.drop_index("ix_user_activity_event_type", table_name="user_activity_events")
    op.drop_index("ix_user_activity_user_id", table_name="user_activity_events")
    op.drop_table("user_activity_events")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("login_count")
        batch_op.drop_column("last_seen_at")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("signature")
        batch_op.drop_column("avatar_updated_at")
        batch_op.drop_column("avatar_content_type")
        batch_op.drop_column("avatar_object_key")
