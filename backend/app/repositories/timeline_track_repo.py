from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent
from app.models.timeline_track import TimelineTrack


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineTrackRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(self, project_id: str) -> list[TimelineTrack]:
        statement = (
            select(TimelineTrack)
            .where(
                TimelineTrack.project_id == project_id,
                TimelineTrack.deleted_at.is_(None),
            )
            .order_by(
                TimelineTrack.is_main.desc(),
                TimelineTrack.order_index.asc(),
                TimelineTrack.created_at.asc(),
            )
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, track_id: str) -> TimelineTrack | None:
        statement = select(TimelineTrack).where(
            TimelineTrack.id == track_id,
            TimelineTrack.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_main_active_by_project(self, project_id: str) -> TimelineTrack | None:
        statement = (
            select(TimelineTrack)
            .where(
                TimelineTrack.project_id == project_id,
                TimelineTrack.deleted_at.is_(None),
                TimelineTrack.is_main.is_(True),
            )
            .order_by(TimelineTrack.order_index.asc(), TimelineTrack.created_at.asc())
        )
        return self.db.scalar(statement)

    def count_active_main_by_project(self, project_id: str) -> int:
        statement = select(func.count()).select_from(TimelineTrack).where(
            TimelineTrack.project_id == project_id,
            TimelineTrack.deleted_at.is_(None),
            TimelineTrack.is_main.is_(True),
        )
        return int(self.db.scalar(statement) or 0)

    def count_active_events_by_track(self, track_id: str) -> int:
        statement = select(func.count()).select_from(TimelineEvent).where(
            TimelineEvent.track_id == track_id,
            TimelineEvent.deleted_at.is_(None),
        )
        return int(self.db.scalar(statement) or 0)

    def create(self, track: TimelineTrack, *, commit: bool = True) -> TimelineTrack:
        self.db.add(track)
        if commit:
            self.db.commit()
            self.db.refresh(track)
        return track

    def update(self, track: TimelineTrack, values: dict[str, object], *, commit: bool = True) -> TimelineTrack:
        for field, value in values.items():
            setattr(track, field, value)

        track.updated_at = utc_now()
        track.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(track)
        return track

    def soft_delete(self, track: TimelineTrack, *, commit: bool = True) -> TimelineTrack:
        now = utc_now()
        track.deleted_at = now
        track.updated_at = now
        track.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(track)
        return track
