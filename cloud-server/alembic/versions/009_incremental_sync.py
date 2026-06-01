"""incremental sync tables

Revision ID: 009_incremental_sync
Revises: 008_scalability_indexes_and_metrics
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_incremental_sync"
down_revision: Union[str, None] = "008_scalability_indexes_and_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cloud_sync_entities ─────────────────────────────────────────
    op.create_table(
        "cloud_sync_entities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("cloud_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_change_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "entity_type",
            "entity_id",
            name="uq_cloud_sync_entities_project_type_id",
        ),
    )
    op.create_index(
        "ix_cloud_sync_entities_owner_id",
        "cloud_sync_entities",
        ["owner_id"],
    )
    op.create_index(
        "ix_cloud_sync_entities_project_id",
        "cloud_sync_entities",
        ["project_id"],
    )
    op.create_index(
        "ix_cloud_sync_entities_owner_project_type",
        "cloud_sync_entities",
        ["owner_id", "project_id", "entity_type"],
    )
    op.create_index(
        "ix_cloud_sync_entities_project_change",
        "cloud_sync_entities",
        ["project_id", "last_change_id"],
    )

    # ── cloud_sync_changes ──────────────────────────────────────────
    op.create_table(
        "cloud_sync_changes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(16), nullable=False, server_default="upsert"),
        sa.Column("cloud_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("device_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cloud_sync_changes_owner_id",
        "cloud_sync_changes",
        ["owner_id"],
    )
    op.create_index(
        "ix_cloud_sync_changes_project_id",
        "cloud_sync_changes",
        ["project_id"],
    )
    op.create_index(
        "ix_cloud_sync_changes_project_cursor",
        "cloud_sync_changes",
        ["project_id", "id"],
    )

    # ── cloud_sync_snapshots ────────────────────────────────────────
    op.create_table(
        "cloud_sync_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("cloud_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(32), nullable=False, server_default="push"),
        sa.Column("device_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cloud_sync_snapshots_owner_id",
        "cloud_sync_snapshots",
        ["owner_id"],
    )
    op.create_index(
        "ix_cloud_sync_snapshots_project_id",
        "cloud_sync_snapshots",
        ["project_id"],
    )
    op.create_index(
        "ix_cloud_sync_snapshots_entity",
        "cloud_sync_snapshots",
        ["project_id", "entity_type", "entity_id"],
    )

    # ── cloud_sync_conflicts ────────────────────────────────────────
    op.create_table(
        "cloud_sync_conflicts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column(
            "winner_payload_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "loser_payload_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "winner_source", sa.String(32), nullable=False, server_default="cloud"
        ),
        sa.Column(
            "loser_source", sa.String(32), nullable=False, server_default="local"
        ),
        sa.Column(
            "winner_device_id", sa.String(128), nullable=False, server_default=""
        ),
        sa.Column(
            "loser_device_id", sa.String(128), nullable=False, server_default=""
        ),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cloud_sync_conflicts_owner_id",
        "cloud_sync_conflicts",
        ["owner_id"],
    )
    op.create_index(
        "ix_cloud_sync_conflicts_project_id",
        "cloud_sync_conflicts",
        ["project_id"],
    )
    op.create_index(
        "ix_cloud_sync_conflicts_project_entity",
        "cloud_sync_conflicts",
        ["project_id", "entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_table("cloud_sync_conflicts")
    op.drop_table("cloud_sync_snapshots")
    op.drop_table("cloud_sync_changes")
    op.drop_table("cloud_sync_entities")
