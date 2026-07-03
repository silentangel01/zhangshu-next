"""email verification codes

Revision ID: 010_email_verification_codes
Revises: 009_incremental_sync
Create Date: 2026-06-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_email_verification_codes"
down_revision: Union[str, None] = "009_incremental_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_codes_id",
        "email_verification_codes",
        ["id"],
    )
    op.create_index(
        "ix_email_verification_codes_email",
        "email_verification_codes",
        ["email"],
    )
    op.create_index(
        "ix_email_verification_codes_purpose",
        "email_verification_codes",
        ["purpose"],
    )
    op.create_index(
        "ix_email_verification_codes_expires_at",
        "email_verification_codes",
        ["expires_at"],
    )
    op.create_index(
        "ix_email_verification_codes_consumed_at",
        "email_verification_codes",
        ["consumed_at"],
    )
    op.create_index(
        "ix_email_verification_codes_lookup",
        "email_verification_codes",
        ["email", "purpose", "consumed_at", "expires_at"],
    )
    op.create_index(
        "ix_email_verification_codes_created_at",
        "email_verification_codes",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_codes_created_at",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_lookup",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_consumed_at",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_expires_at",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_purpose",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_email",
        table_name="email_verification_codes",
    )
    op.drop_index(
        "ix_email_verification_codes_id",
        table_name="email_verification_codes",
    )
    op.drop_table("email_verification_codes")
