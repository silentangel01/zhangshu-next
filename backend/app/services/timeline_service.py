from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.setting_repo import SettingRepository
from app.repositories.timeline_repo import TimelineRepository
from app.schemas.timeline import TimelineEventCreate, TimelineEventUpdate
from app.services.timeline_track_service import TimelineTrackService


class TimelineEventNotFoundError(Exception):
    pass


class TimelineProjectNotFoundError(Exception):
    pass


class TimelineChapterNotFoundError(Exception):
    pass


class TimelineChapterProjectMismatchError(Exception):
    pass


class TimelineSettingNotFoundError(Exception):
    pass


class TimelineSettingProjectMismatchError(Exception):
    pass


class TimelineService:
    def __init__(self, db: Session):
        self.db = db
        self.timeline_repo = TimelineRepository(db)
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.setting_repo = SettingRepository(db)
        self.track_service = TimelineTrackService(db)

    def list_project_timeline_events(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
        status: str | None = None,
        importance: str | None = None,
        chapter_id: str | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, object]]:
        self._ensure_project_exists(project_id)
        self.track_service.ensure_main_track(project_id)

        events = self.timeline_repo.list_active_by_project(
            project_id,
            event_type=event_type,
            status=status,
            importance=importance,
            chapter_id=chapter_id,
            keyword=keyword,
        )
        return self._attach_related_objects(events)

    def list_chapter_timeline_events(self, chapter_id: str) -> list[dict[str, object]]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise TimelineChapterNotFoundError

        self.track_service.ensure_main_track(chapter.project_id)
        return self._attach_related_objects(self.timeline_repo.list_active_by_chapter(chapter_id))

    def create_timeline_event(self, project_id: str, data: TimelineEventCreate) -> dict[str, object]:
        self._ensure_project_exists(project_id)
        self._validate_chapter(project_id, data.chapter_id)
        self._validate_setting(project_id, data.location_setting_id)

        values = data.model_dump()
        track = self.track_service.validate_track_for_project(project_id, values.get("track_id"))
        values["track_id"] = track.id
        if values.get("position_ratio") is None:
            values["position_ratio"] = self._suggest_position_ratio(track.id)

        event = TimelineEvent(id=str(uuid4()), project_id=project_id, **values)
        created = self.timeline_repo.create(event)
        self._mark_dirty(project_id, created.id, "upsert")
        return self._to_read_payload(created)

    def get_timeline_event(self, event_id: str) -> dict[str, object]:
        event = self.timeline_repo.get_active(event_id)
        if event is None:
            raise TimelineEventNotFoundError
        return self._to_read_payload(event)

    def update_timeline_event(self, event_id: str, data: TimelineEventUpdate) -> dict[str, object]:
        event = self.timeline_repo.get_active(event_id)
        if event is None:
            raise TimelineEventNotFoundError

        values = data.model_dump(exclude_unset=True)
        if "chapter_id" in values:
            self._validate_chapter(event.project_id, values["chapter_id"])
        if "location_setting_id" in values:
            self._validate_setting(event.project_id, values["location_setting_id"])
        if "track_id" in values:
            track = self.track_service.validate_track_for_project(event.project_id, values["track_id"])
            values["track_id"] = track.id
            if values.get("position_ratio") is None:
                values["position_ratio"] = self._suggest_position_ratio(track.id)
        if "position_ratio" in values and values["position_ratio"] is None:
            values.pop("position_ratio")

        updated = self.timeline_repo.update(event, values)
        self._mark_dirty(event.project_id, event_id, "upsert")
        return self._to_read_payload(updated)

    def delete_timeline_event(self, event_id: str) -> dict[str, object]:
        event = self.timeline_repo.get_active(event_id)
        if event is None:
            raise TimelineEventNotFoundError
        deleted = self.timeline_repo.soft_delete(event)
        self._mark_dirty(event.project_id, event_id, "delete")
        return self._to_read_payload(deleted)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise TimelineProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark the timeline event as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "timeline_events", entity_id, action)
        except Exception:
            pass

    def _validate_chapter(self, project_id: str, chapter_id: object) -> None:
        if chapter_id is None:
            return
        chapter = self.chapter_repo.get_active(str(chapter_id))
        if chapter is None:
            raise TimelineChapterNotFoundError
        if chapter.project_id != project_id:
            raise TimelineChapterProjectMismatchError

    def _validate_setting(self, project_id: str, setting_id: object) -> None:
        if setting_id is None:
            return
        setting = self.setting_repo.get_active(str(setting_id))
        if setting is None:
            raise TimelineSettingNotFoundError
        if setting.project_id != project_id:
            raise TimelineSettingProjectMismatchError

    def _attach_related_objects(self, events: list[TimelineEvent]) -> list[dict[str, object]]:
        chapter_cache: dict[str, object | None] = {}
        setting_cache: dict[str, object | None] = {}
        payloads: list[dict[str, object]] = []

        for event in events:
            payloads.append(
                self._to_read_payload(
                    event,
                    chapter_cache=chapter_cache,
                    setting_cache=setting_cache,
                )
            )

        return payloads

    def _to_read_payload(
        self,
        event: TimelineEvent,
        *,
        chapter_cache: dict[str, object | None] | None = None,
        setting_cache: dict[str, object | None] | None = None,
    ) -> dict[str, object]:
        chapter = None
        if event.chapter_id is not None:
            chapter = self._get_cached_chapter(event.chapter_id, chapter_cache)

        location_setting = None
        if event.location_setting_id is not None:
            location_setting = self._get_cached_setting(event.location_setting_id, setting_cache)

        return {
            "id": event.id,
            "project_id": event.project_id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "story_date": event.story_date,
            "story_time": event.story_time,
            "order_index": event.order_index,
            "position_index": event.position_index,
            "position_ratio": event.position_ratio,
            "importance": event.importance,
            "status": event.status,
            "chapter_id": event.chapter_id,
            "location_setting_id": event.location_setting_id,
            "track_id": event.track_id,
            "note": event.note,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            "deleted_at": event.deleted_at,
            "version": event.version,
            "chapter": chapter,
            "location_setting": location_setting,
        }

    def _get_cached_chapter(
        self,
        chapter_id: str,
        cache: dict[str, object | None] | None,
    ) -> object | None:
        if cache is None:
            return self.chapter_repo.get_active(chapter_id)
        if chapter_id not in cache:
            cache[chapter_id] = self.chapter_repo.get_active(chapter_id)
        return cache[chapter_id]

    def _get_cached_setting(
        self,
        setting_id: str,
        cache: dict[str, object | None] | None,
    ) -> object | None:
        if cache is None:
            return self.setting_repo.get_active(setting_id)
        if setting_id not in cache:
            cache[setting_id] = self.setting_repo.get_active(setting_id)
        return cache[setting_id]

    def _suggest_position_ratio(self, track_id: str) -> float:
        events = self.timeline_repo.list_active_by_track(track_id)
        ratios = [float(event.position_ratio) for event in events if event.position_ratio is not None]
        if not ratios:
            return 50.0

        candidate = max(ratios) + 8.0
        if candidate <= 92.0:
            return round(candidate, 2)

        candidate = min(ratios) - 8.0
        if candidate >= 8.0:
            return round(candidate, 2)

        return round(100.0 * (len(ratios) + 1) / (len(ratios) + 2), 2)
