from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.timeline_track import TimelineTrack
from app.repositories.project_repo import ProjectRepository
from app.repositories.timeline_repo import TimelineRepository
from app.repositories.timeline_track_repo import TimelineTrackRepository
from app.schemas.timeline import TimelineTrackCreate, TimelineTrackUpdate


class TimelineProjectNotFoundError(Exception):
    pass


class TimelineTrackNotFoundError(Exception):
    pass


class TimelineTrackProjectMismatchError(Exception):
    pass


class TimelineTrackHasEventsError(Exception):
    pass


class TimelineTrackMainRequiredError(Exception):
    pass


class TimelineTrackService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.track_repo = TimelineTrackRepository(db)
        self.timeline_repo = TimelineRepository(db)

    def list_project_timeline_tracks(self, project_id: str) -> list[TimelineTrack]:
        self._ensure_project_exists(project_id)
        self.ensure_main_track(project_id)
        return self.track_repo.list_active_by_project(project_id)

    def create_timeline_track(self, project_id: str, data: TimelineTrackCreate) -> TimelineTrack:
        self._ensure_project_exists(project_id)
        track = TimelineTrack(
            id=str(uuid4()),
            project_id=project_id,
            title=data.title,
            description=data.description,
            track_type=data.track_type,
            bound_type=data.bound_type,
            bound_id=data.bound_id,
            order_index=data.order_index,
            color=data.color,
            is_main=data.is_main,
        )
        created = self.track_repo.create(track)
        self._mark_dirty(project_id, created.id, "upsert")
        return created

    def get_timeline_track(self, track_id: str) -> TimelineTrack:
        track = self.track_repo.get_active(track_id)
        if track is None:
            raise TimelineTrackNotFoundError
        return track

    def update_timeline_track(self, track_id: str, data: TimelineTrackUpdate) -> TimelineTrack:
        track = self.get_timeline_track(track_id)
        values = data.model_dump(exclude_unset=True)

        if "is_main" in values and values["is_main"] is False and track.is_main:
            if self.track_repo.count_active_main_by_project(track.project_id) <= 1:
                raise TimelineTrackMainRequiredError

        updated = self.track_repo.update(track, values)
        self._mark_dirty(track.project_id, track_id, "upsert")
        return updated

    def delete_timeline_track(self, track_id: str) -> TimelineTrack:
        track = self.get_timeline_track(track_id)
        if self.track_repo.count_active_events_by_track(track.id) > 0:
            raise TimelineTrackHasEventsError

        if track.is_main and self.track_repo.count_active_main_by_project(track.project_id) <= 1:
            raise TimelineTrackMainRequiredError

        deleted = self.track_repo.soft_delete(track)
        self._mark_dirty(track.project_id, track_id, "delete")
        return deleted

    def ensure_main_track(self, project_id: str) -> TimelineTrack:
        self._ensure_project_exists(project_id)
        main_track = self.track_repo.get_main_active_by_project(project_id)
        created_main_track = False
        if main_track is None:
            main_track = TimelineTrack(
                id=str(uuid4()),
                project_id=project_id,
                title="全书主时间轴",
                description="",
                track_type="main",
                bound_type=None,
                bound_id=None,
                order_index=0,
                color=None,
                is_main=True,
            )
            self.track_repo.create(main_track, commit=False)
            self.db.flush()
            created_main_track = True

        self.timeline_repo.backfill_untracked_events(project_id, main_track.id, commit=False)
        if created_main_track:
            self._distribute_track_position_ratios(main_track.id)
        self.db.commit()
        self.db.refresh(main_track)
        return main_track

    def validate_track_for_project(self, project_id: str, track_id: str | None) -> TimelineTrack:
        if track_id is None:
            return self.ensure_main_track(project_id)

        track = self.get_timeline_track(track_id)
        if track.project_id != project_id:
            raise TimelineTrackProjectMismatchError
        return track

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise TimelineProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark the timeline track as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "timeline_tracks", entity_id, action)
        except Exception:
            pass

    def _distribute_track_position_ratios(self, track_id: str) -> None:
        events = self.timeline_repo.list_active_by_track(track_id)
        event_count = len(events)
        if event_count == 0:
            return

        for index, event in enumerate(events):
            if event_count == 1:
                event.position_ratio = 50.0
            else:
                event.position_ratio = round(100.0 * (index + 1) / (event_count + 1), 2)
