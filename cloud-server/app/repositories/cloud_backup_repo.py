"""Cloud backup data access layer."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cloud_backup import CloudBackup


class CloudBackupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, backup_id: str) -> CloudBackup | None:
        return self.db.scalar(
            select(CloudBackup).where(
                CloudBackup.id == backup_id,
                CloudBackup.deleted_at.is_(None),
            )
        )

    def get_by_upload_id(self, upload_id: str) -> CloudBackup | None:
        return self.db.scalar(
            select(CloudBackup).where(
                CloudBackup.upload_id == upload_id,
                CloudBackup.deleted_at.is_(None),
            )
        )

    def get_by_project(
        self, project_id: str
    ) -> list[CloudBackup]:
        statement = (
            select(CloudBackup)
            .where(
                CloudBackup.project_id == project_id,
                CloudBackup.deleted_at.is_(None),
            )
            .order_by(CloudBackup.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def count_by_project(self, project_id: str) -> int:
        statement = select(func.count()).select_from(
            select(CloudBackup)
            .where(
                CloudBackup.project_id == project_id,
                CloudBackup.deleted_at.is_(None),
            )
            .subquery()
        )
        return self.db.scalar(statement) or 0

    def create(
        self, backup: CloudBackup, *, commit: bool = True
    ) -> CloudBackup:
        self.db.add(backup)
        if commit:
            self.db.commit()
            self.db.refresh(backup)
        return backup

    def update(
        self,
        backup: CloudBackup,
        values: dict,
        *,
        commit: bool = True,
    ) -> CloudBackup:
        for key, value in values.items():
            setattr(backup, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(backup)
        return backup

    def soft_delete(
        self, backup: CloudBackup, *, commit: bool = True
    ) -> None:
        from app.models.user import utc_now

        backup.deleted_at = utc_now()
        if commit:
            self.db.commit()
