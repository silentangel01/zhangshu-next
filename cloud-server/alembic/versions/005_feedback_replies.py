"""feedback replies table

Revision ID: 005_feedback_replies
Revises: 004_admin_dashboard_profile
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_feedback_replies"
down_revision: Union[str, None] = "004_admin_dashboard_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_replies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.String(36),
            sa.ForeignKey("feedback_tickets.id"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "author_type",
            sa.String(16),
            nullable=False,
            server_default="admin",
            comment="admin | system",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_feedback_replies_ticket_created",
        "feedback_replies",
        ["ticket_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_replies_ticket_created", table_name="feedback_replies")
    op.drop_table("feedback_replies")
