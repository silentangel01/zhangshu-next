from datetime import datetime, timezone

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.models.writing_stat_event import WritingStatEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WritingStatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self,
        event: WritingStatEvent,
        *,
        commit: bool = True,
    ) -> WritingStatEvent:
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        return event

    def list_event_dates(self, project_id: str) -> list[str]:
        statement = (
            select(WritingStatEvent.local_date)
            .where(WritingStatEvent.project_id == project_id)
            .distinct()
            .order_by(WritingStatEvent.local_date.asc())
        )
        return list(self.db.scalars(statement).all())

    def aggregate_daily(
        self,
        project_id: str,
        start_date: str,
        end_date: str,
    ) -> list[Row]:
        statement = (
            select(
                WritingStatEvent.local_date,
                func.sum(WritingStatEvent.delta_words).label("net_words"),
                func.sum(WritingStatEvent.added_words).label("added_words"),
                func.sum(WritingStatEvent.deleted_words).label("deleted_words"),
                func.count(WritingStatEvent.id).label("event_count"),
            )
            .where(
                WritingStatEvent.project_id == project_id,
                WritingStatEvent.local_date >= start_date,
                WritingStatEvent.local_date <= end_date,
            )
            .group_by(WritingStatEvent.local_date)
            .order_by(WritingStatEvent.local_date.asc())
        )
        return list(self.db.execute(statement).all())

    def aggregate_hourly(
        self,
        project_id: str,
        start_date: str,
        end_date: str,
    ) -> list[Row]:
        statement = (
            select(
                WritingStatEvent.local_hour,
                func.sum(WritingStatEvent.delta_words).label("net_words"),
                func.count(WritingStatEvent.id).label("event_count"),
            )
            .where(
                WritingStatEvent.project_id == project_id,
                WritingStatEvent.local_date >= start_date,
                WritingStatEvent.local_date <= end_date,
            )
            .group_by(WritingStatEvent.local_hour)
            .order_by(WritingStatEvent.local_hour.asc())
        )
        return list(self.db.execute(statement).all())

    def aggregate_chapter_delta(
        self,
        project_id: str,
        start_date: str,
        end_date: str,
    ) -> list[Row]:
        statement = (
            select(
                WritingStatEvent.chapter_id,
                func.sum(WritingStatEvent.delta_words).label("delta_words"),
            )
            .where(
                WritingStatEvent.project_id == project_id,
                WritingStatEvent.local_date >= start_date,
                WritingStatEvent.local_date <= end_date,
            )
            .group_by(WritingStatEvent.chapter_id)
        )
        return list(self.db.execute(statement).all())

    def list_events_by_project_in_range(
        self,
        project_id: str,
        start_date: str,
        end_date: str,
    ) -> list[WritingStatEvent]:
        statement = (
            select(WritingStatEvent)
            .where(
                WritingStatEvent.project_id == project_id,
                WritingStatEvent.local_date >= start_date,
                WritingStatEvent.local_date <= end_date,
            )
            .order_by(WritingStatEvent.occurred_at.asc())
        )
        return list(self.db.scalars(statement).all())
