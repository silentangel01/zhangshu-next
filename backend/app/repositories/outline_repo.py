from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outline_item import OutlineItem
from app.schemas.outline import OutlineReorderItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutlineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        volume_id: str | None = None,
        chapter_id: str | None = None,
        item_type: str | None = None,
        status: str | None = None,
    ) -> list[OutlineItem]:
        statement = select(OutlineItem).where(
            OutlineItem.project_id == project_id,
            OutlineItem.deleted_at.is_(None),
        )

        if volume_id is not None:
            statement = statement.where(OutlineItem.volume_id == volume_id)
        if chapter_id is not None:
            statement = statement.where(OutlineItem.chapter_id == chapter_id)
        if item_type is not None:
            statement = statement.where(OutlineItem.item_type == item_type)
        if status is not None:
            statement = statement.where(OutlineItem.status == status)

        statement = statement.order_by(
            OutlineItem.parent_id.asc(),
            OutlineItem.order_index.asc(),
            OutlineItem.created_at.asc(),
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, outline_id: str) -> OutlineItem | None:
        statement = select(OutlineItem).where(
            OutlineItem.id == outline_id,
            OutlineItem.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, outline: OutlineItem) -> OutlineItem:
        self.db.add(outline)
        self.db.commit()
        self.db.refresh(outline)
        return outline

    def update(self, outline: OutlineItem, values: dict[str, object]) -> OutlineItem:
        for field, value in values.items():
            setattr(outline, field, value)

        outline.updated_at = utc_now()
        outline.version += 1
        self.db.commit()
        self.db.refresh(outline)
        return outline

    def soft_delete(self, outline: OutlineItem) -> OutlineItem:
        now = utc_now()
        outline.deleted_at = now
        outline.updated_at = now
        outline.version += 1
        self.db.commit()
        self.db.refresh(outline)
        return outline

    def batch_reorder(self, items: list[OutlineReorderItem]) -> int:
        now = utc_now()
        updated = 0
        for item in items:
            outline = self.get_active(item.outline_id)
            if outline is None:
                continue
            if outline.parent_id != item.parent_id or outline.order_index != item.order_index:
                outline.parent_id = item.parent_id
                outline.order_index = item.order_index
                outline.updated_at = now
                outline.version += 1
                updated += 1
        if updated > 0:
            self.db.commit()
        return updated
