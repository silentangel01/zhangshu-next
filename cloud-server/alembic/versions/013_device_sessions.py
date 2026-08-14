"""stable device sessions

Revision ID: 013_device_sessions
Revises: 012_oauth_login_sessions
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013_device_sessions"
down_revision: Union[str, None] = "012_oauth_login_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.add_column(sa.Column("session_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("device_id", sa.String(128), nullable=True))
        batch.add_column(sa.Column("device_name", sa.String(255), nullable=True))
    op.execute("UPDATE refresh_tokens SET session_id = id WHERE session_id IS NULL")
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("session_id", nullable=False)
        batch.create_index("ix_refresh_tokens_session_id", ["session_id"])
        batch.create_index("ix_refresh_tokens_device_id", ["device_id"])

    with op.batch_alter_table("oauth_login_sessions") as batch:
        batch.add_column(sa.Column("device_id", sa.String(128), nullable=True))
        batch.add_column(sa.Column("device_name", sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("oauth_login_sessions") as batch:
        batch.drop_column("device_name")
        batch.drop_column("device_id")
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.drop_index("ix_refresh_tokens_device_id")
        batch.drop_index("ix_refresh_tokens_session_id")
        batch.drop_column("device_name")
        batch.drop_column("device_id")
        batch.drop_column("session_id")
