"""announcements and feedback tables

Revision ID: 003_announcements_feedback
Revises: 002_account_privacy
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_announcements_feedback"
down_revision: Union[str, None] = "002_account_privacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: is_admin flag ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.create_index("ix_users_is_admin", ["is_admin"])

    # --- announcements ---
    op.create_table(
        "announcements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False, server_default="info"),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("audience", sa.String(24), nullable=False, server_default="all"),
        sa.Column("platform", sa.String(32), nullable=True),
        sa.Column("min_app_version", sa.String(32), nullable=True),
        sa.Column("max_app_version", sa.String(32), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_announcements_status_time",
        "announcements",
        ["status", "starts_at", "ends_at"],
    )
    op.create_index(
        "ix_announcements_platform_status",
        "announcements",
        ["platform", "status"],
    )

    # --- feedback_tickets ---
    op.create_table(
        "feedback_tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(16), nullable=True),
        sa.Column("app_version", sa.String(64), nullable=True),
        sa.Column("platform", sa.String(64), nullable=True),
        sa.Column("network_mode", sa.String(32), nullable=True),
        sa.Column("client_diagnostics_json", sa.Text(), nullable=True),
        sa.Column(
            "attachment_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_size_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_feedback_user_created", "feedback_tickets", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_feedback_status_created", "feedback_tickets", ["status", "created_at"]
    )
    op.create_index(
        "ix_feedback_category_created",
        "feedback_tickets",
        ["category", "created_at"],
    )

    # --- feedback_attachments ---
    op.create_table(
        "feedback_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "feedback_id",
            sa.String(36),
            sa.ForeignKey("feedback_tickets.id"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="uploading"
        ),
        sa.Column(
            "upload_id", sa.String(64), unique=True, index=True, nullable=False
        ),
        sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_feedback_att_feedback_status",
        "feedback_attachments",
        ["feedback_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("feedback_attachments")
    op.drop_table("feedback_tickets")
    op.drop_table("announcements")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_is_admin")
        batch_op.drop_column("is_admin")
