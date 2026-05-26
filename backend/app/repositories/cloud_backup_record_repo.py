from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cloud_backup_record import CloudBackupRecord


class CloudBackupRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_project(
        self, project_id: str, cloud_user_id: str
    ) -> list[CloudBackupRecord]:
        statement = (
            select(CloudBackupRecord)
            .where(
                CloudBackupRecord.project_id == project_id,
                CloudBackupRecord.cloud_user_id == cloud_user_id,
                CloudBackupRecord.deleted_at.is_(None),
            )
            .order_by(CloudBackupRecord.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get(self, record_id: str) -> CloudBackupRecord | None:
        return self.db.scalar(
            select(CloudBackupRecord).where(
                CloudBackupRecord.id == record_id,
                CloudBackupRecord.deleted_at.is_(None),
            )
        )

    def get_by_cloud_backup_id(
        self, cloud_backup_id: str
    ) -> CloudBackupRecord | None:
        return self.db.scalar(
            select(CloudBackupRecord).where(
                CloudBackupRecord.cloud_backup_id == cloud_backup_id,
                CloudBackupRecord.deleted_at.is_(None),
            )
        )

    def create(
        self, record: CloudBackupRecord, *, commit: bool = True
    ) -> CloudBackupRecord:
        self.db.add(record)
        if commit:
            self.db.commit()
            self.db.refresh(record)
        return record

    def update(
        self,
        record: CloudBackupRecord,
        values: dict,
        *,
        commit: bool = True,
    ) -> CloudBackupRecord:
        for key, value in values.items():
            setattr(record, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(record)
        return record

    def soft_delete(
        self, record: CloudBackupRecord, *, commit: bool = True
    ) -> None:
        record.deleted_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()
