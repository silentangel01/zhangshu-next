"""account privacy and abuse prevention fields

Revision ID: 002_account_privacy
Revises: 001_initial
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_account_privacy"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: privacy / deletion fields ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("privacy_version_accepted", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    # --- refresh_tokens: session tracking fields ---
    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.add_column(sa.Column("user_agent", sa.String(512), nullable=True))
        batch_op.add_column(sa.Column("client_ip", sa.String(45), nullable=True))
        batch_op.add_column(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("revoked_reason", sa.String(64), nullable=True))

    # --- rate_limit_events ---
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope", sa.String(32), nullable=False, index=True),
        sa.Column("key", sa.String(128), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=True, index=True),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # --- account_deletion_requests ---
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("confirm_token_hash", sa.String(64), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("account_deletion_requests")
    op.drop_table("rate_limit_events")

    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.drop_column("revoked_reason")
        batch_op.drop_column("last_used_at")
        batch_op.drop_column("client_ip")
        batch_op.drop_column("user_agent")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("privacy_version_accepted")
        batch_op.drop_column("anonymized_at")
        batch_op.drop_column("deletion_requested_at")
        batch_op.drop_column("deleted_at")
