from datetime import datetime, timezone

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
        status: str | None = None,
        importance: str | None = None,
        chapter_id: str | None = None,
        keyword: str | None = None,
    ) -> list[TimelineEvent]:
        statement = select(TimelineEvent).where(
            TimelineEvent.project_id == project_id,
            TimelineEvent.deleted_at.is_(None),
        )

        if event_type is not None:
            statement = statement.where(TimelineEvent.event_type == event_type)
        if status is not None:
            statement = statement.where(TimelineEvent.status == status)
        if importance is not None:
            statement = statement.where(TimelineEvent.importance == importance)
        if chapter_id is not None:
            statement = statement.where(TimelineEvent.chapter_id == chapter_id)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    TimelineEvent.title.ilike(pattern),
                    TimelineEvent.description.ilike(pattern),
                    TimelineEvent.story_date.ilike(pattern),
                    TimelineEvent.note.ilike(pattern),
                )
            )

        statement = statement.order_by(
            TimelineEvent.order_index.asc(),
            TimelineEvent.position_index.asc(),
            case((TimelineEvent.story_date.is_(None), 1), else_=0).asc(),
            TimelineEvent.story_date.asc(),
            TimelineEvent.created_at.asc(),
        )
        return list(self.db.scalars(statement).all())

    def list_active_by_chapter(self, chapter_id: str) -> list[TimelineEvent]:
        statement = (
            select(TimelineEvent)
            .where(
                TimelineEvent.chapter_id == chapter_id,
                TimelineEvent.deleted_at.is_(None),
            )
            .order_by(
                TimelineEvent.order_index.asc(),
                TimelineEvent.position_index.asc(),
                TimelineEvent.created_at.asc(),
            )
        )
        return list(self.db.scalars(statement).all())

    def list_active_untracked_by_project(self, project_id: str) -> list[TimelineEvent]:
        statement = (
            select(TimelineEvent)
            .where(
                TimelineEvent.project_id == project_id,
                TimelineEvent.deleted_at.is_(None),
                TimelineEvent.track_id.is_(None),
            )
            .order_by(
                TimelineEvent.order_index.asc(),
                TimelineEvent.position_index.asc(),
                TimelineEvent.created_at.asc(),
            )
        )
        return list(self.db.scalars(statement).all())

    def count_active_by_track(self, track_id: str) -> int:
        statement = select(func.count()).select_from(TimelineEvent).where(
            TimelineEvent.track_id == track_id,
            TimelineEvent.deleted_at.is_(None),
        )
        return int(self.db.scalar(statement) or 0)

    def backfill_untracked_events(self, project_id: str, track_id: str, *, commit: bool = True) -> int:
        statement = (
            update(TimelineEvent)
            .where(
                TimelineEvent.project_id == project_id,
                TimelineEvent.deleted_at.is_(None),
                TimelineEvent.track_id.is_(None),
            )
            .values(track_id=track_id, position_index=TimelineEvent.order_index)
        )
        result = self.db.execute(statement)
        if commit:
            self.db.commit()
        return int(result.rowcount or 0)

    def get_active(self, event_id: str) -> TimelineEvent | None:
        statement = select(TimelineEvent).where(
            TimelineEvent.id == event_id,
            TimelineEvent.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, event: TimelineEvent) -> TimelineEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update(self, event: TimelineEvent, values: dict[str, object]) -> TimelineEvent:
        for field, value in values.items():
            setattr(event, field, value)

        event.updated_at = utc_now()
        event.version += 1
        self.db.commit()
        self.db.refresh(event)
        return event

    def soft_delete(self, event: TimelineEvent) -> TimelineEvent:
        now = utc_now()
        event.deleted_at = now
        event.updated_at = now
        event.version += 1
        self.db.commit()
        self.db.refresh(event)
        return event
