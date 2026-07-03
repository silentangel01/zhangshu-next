"""auth identities and phone verification

Revision ID: 011_auth_identities_phone
Revises: 010_email_verification_codes
Create Date: 2026-06-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_auth_identities_phone"
down_revision: Union[str, None] = "010_email_verification_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_auth_identities",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "identifier", name="uq_auth_identity_provider_identifier"),
        sa.UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
    )
    op.create_index("ix_user_auth_identities_id", "user_auth_identities", ["id"])
    op.create_index("ix_user_auth_identities_user_id", "user_auth_identities", ["user_id"])
    op.create_index("ix_user_auth_identities_provider", "user_auth_identities", ["provider"])
    op.create_index("ix_user_auth_identities_identifier", "user_auth_identities", ["identifier"])

    op.execute(
        """
        INSERT INTO user_auth_identities
            (id, user_id, provider, identifier, verified_at, created_at, updated_at)
        SELECT
            'email-' || md5(email),
            id,
            'email',
            lower(email),
            created_at,
            created_at,
            updated_at
        FROM users
        WHERE email NOT LIKE '%@deleted.local'
          AND email NOT LIKE '%@phone.zhangshu.local'
        ON CONFLICT DO NOTHING
        """
    )

    op.create_table(
        "phone_verification_codes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
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
    op.create_index("ix_phone_verification_codes_id", "phone_verification_codes", ["id"])
    op.create_index("ix_phone_verification_codes_phone_number", "phone_verification_codes", ["phone_number"])
    op.create_index("ix_phone_verification_codes_purpose", "phone_verification_codes", ["purpose"])
    op.create_index("ix_phone_verification_codes_expires_at", "phone_verification_codes", ["expires_at"])
    op.create_index("ix_phone_verification_codes_consumed_at", "phone_verification_codes", ["consumed_at"])
    op.create_index(
        "ix_phone_verification_codes_lookup",
        "phone_verification_codes",
        ["phone_number", "purpose", "consumed_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_phone_verification_codes_lookup", table_name="phone_verification_codes")
    op.drop_index("ix_phone_verification_codes_consumed_at", table_name="phone_verification_codes")
    op.drop_index("ix_phone_verification_codes_expires_at", table_name="phone_verification_codes")
    op.drop_index("ix_phone_verification_codes_purpose", table_name="phone_verification_codes")
    op.drop_index("ix_phone_verification_codes_phone_number", table_name="phone_verification_codes")
    op.drop_index("ix_phone_verification_codes_id", table_name="phone_verification_codes")
    op.drop_table("phone_verification_codes")
    op.drop_index("ix_user_auth_identities_identifier", table_name="user_auth_identities")
    op.drop_index("ix_user_auth_identities_provider", table_name="user_auth_identities")
    op.drop_index("ix_user_auth_identities_user_id", table_name="user_auth_identities")
    op.drop_index("ix_user_auth_identities_id", table_name="user_auth_identities")
    op.drop_table("user_auth_identities")
