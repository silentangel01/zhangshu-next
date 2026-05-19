from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.volume import Volume


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VolumeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(self, project_id: str) -> list[Volume]:
        statement = (
            select(Volume)
            .where(
                Volume.project_id == project_id,
                Volume.deleted_at.is_(None),
            )
            .order_by(Volume.order_index.asc(), Volume.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, volume_id: str) -> Volume | None:
        statement = select(Volume).where(
            Volume.id == volume_id,
            Volume.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, volume: Volume) -> Volume:
        self.db.add(volume)
        self.db.commit()
        self.db.refresh(volume)
        return volume

    def update(self, volume: Volume, values: dict[str, object]) -> Volume:
        for field, value in values.items():
            setattr(volume, field, value)

        volume.updated_at = utc_now()
        volume.version += 1
        self.db.commit()
        self.db.refresh(volume)
        return volume

    def soft_delete(self, volume: Volume) -> Volume:
        now = utc_now()
        volume.deleted_at = now
        volume.updated_at = now
        volume.version += 1
        self.db.commit()
        self.db.refresh(volume)
        return volume
