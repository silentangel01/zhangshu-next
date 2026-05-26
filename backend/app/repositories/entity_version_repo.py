from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.entity_version import EntityVersion


class EntityVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, version_id: str) -> EntityVersion | None:
        return self.db.scalar(
            select(EntityVersion).where(
                EntityVersion.id == version_id,
                EntityVersion.deleted_at.is_(None),
            )
        )

    def list_by_project(
        self,
        project_id: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        source: str | None = None,
        pinned: bool | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EntityVersion], int]:
        base = select(EntityVersion).where(
            EntityVersion.project_id == project_id,
            EntityVersion.deleted_at.is_(None),
        )

        if entity_type:
            base = base.where(EntityVersion.entity_type == entity_type)
        if entity_id:
            base = base.where(EntityVersion.entity_id == entity_id)
        if source:
            base = base.where(EntityVersion.source == source)
        if pinned is not None:
            base = base.where(EntityVersion.is_pinned == pinned)
        if keyword:
            pattern = f"%{keyword}%"
            base = base.where(
                EntityVersion.entity_title.like(pattern)
                | EntityVersion.label.like(pattern)
                | EntityVersion.note.like(pattern)
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = base.order_by(EntityVersion.created_at.desc()).limit(limit).offset(offset)
        rows = list(self.db.scalars(stmt).all())
        return rows, total

    def list_by_entity(
        self, project_id: str, entity_type: str, entity_id: str
    ) -> list[EntityVersion]:
        return list(
            self.db.scalars(
                select(EntityVersion)
                .where(
                    EntityVersion.project_id == project_id,
                    EntityVersion.entity_type == entity_type,
                    EntityVersion.entity_id == entity_id,
                    EntityVersion.deleted_at.is_(None),
                )
                .order_by(EntityVersion.created_at.desc())
            ).all()
        )

    def create(self, version: EntityVersion, *, commit: bool = True) -> EntityVersion:
        self.db.add(version)
        if commit:
            self.db.commit()
            self.db.refresh(version)
        return version

    def update(
        self,
        version: EntityVersion,
        values: dict,
        *,
        commit: bool = True,
    ) -> EntityVersion:
        for key, value in values.items():
            setattr(version, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(version)
        return version

    def soft_delete(self, version: EntityVersion, *, commit: bool = True) -> None:
        from datetime import datetime, timezone

        version.deleted_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()
