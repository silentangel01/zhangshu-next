"""oauth login sessions

Revision ID: 012_oauth_login_sessions
Revises: 011_auth_identities_phone
Create Date: 2026-06-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_oauth_login_sessions"
down_revision: Union[str, None] = "011_auth_identities_phone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_login_sessions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("poll_token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("token_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash", name="uq_oauth_login_sessions_state_hash"),
    )
    op.create_index("ix_oauth_login_sessions_id", "oauth_login_sessions", ["id"])
    op.create_index("ix_oauth_login_sessions_provider", "oauth_login_sessions", ["provider"])
    op.create_index("ix_oauth_login_sessions_state_hash", "oauth_login_sessions", ["state_hash"])
    op.create_index("ix_oauth_login_sessions_expires_at", "oauth_login_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_login_sessions_expires_at", table_name="oauth_login_sessions")
    op.drop_index("ix_oauth_login_sessions_state_hash", table_name="oauth_login_sessions")
    op.drop_index("ix_oauth_login_sessions_provider", table_name="oauth_login_sessions")
    op.drop_index("ix_oauth_login_sessions_id", table_name="oauth_login_sessions")
    op.drop_table("oauth_login_sessions")
