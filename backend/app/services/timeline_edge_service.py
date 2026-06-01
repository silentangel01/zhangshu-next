from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.timeline_edge import TimelineEdge
from app.repositories.project_repo import ProjectRepository
from app.repositories.timeline_edge_repo import TimelineEdgeRepository
from app.repositories.timeline_repo import TimelineRepository
from app.schemas.timeline import TimelineEdgeCreate, TimelineEdgeUpdate


class TimelineEdgeProjectNotFoundError(Exception):
    pass


class TimelineEdgeNotFoundError(Exception):
    pass


class TimelineEdgeEventNotFoundError(Exception):
    pass


class TimelineEdgeEventProjectMismatchError(Exception):
    pass


class TimelineEdgeSelfReferenceError(Exception):
    pass


TimelineProjectNotFoundError = TimelineEdgeProjectNotFoundError


class TimelineEdgeService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.edge_repo = TimelineEdgeRepository(db)

    def list_project_timeline_edges(
        self,
        project_id: str,
        *,
        edge_type: str | None = None,
        visibility: str | None = None,
    ) -> list[TimelineEdge]:
        self._ensure_project_exists(project_id)
        return self.edge_repo.list_active_by_project(
            project_id,
            edge_type=edge_type,
            visibility=visibility,
        )

    def create_timeline_edge(self, project_id: str, data: TimelineEdgeCreate) -> TimelineEdge:
        self._ensure_project_exists(project_id)
        self._validate_event_pair(project_id, data.from_event_id, data.to_event_id)

        edge = TimelineEdge(
            id=str(uuid4()),
            project_id=project_id,
            from_event_id=data.from_event_id,
            to_event_id=data.to_event_id,
            edge_type=data.edge_type,
            temporal_relation=data.temporal_relation,
            line_style=data.line_style,
            label=data.label,
            note=data.note,
            visibility=data.visibility,
        )
        created = self.edge_repo.create(edge)
        self._mark_dirty(project_id, created.id, "upsert")
        return created

    def get_timeline_edge(self, edge_id: str) -> TimelineEdge:
        edge = self.edge_repo.get_active(edge_id)
        if edge is None:
            raise TimelineEdgeNotFoundError
        return edge

    def update_timeline_edge(self, edge_id: str, data: TimelineEdgeUpdate) -> TimelineEdge:
        edge = self.get_timeline_edge(edge_id)
        values = data.model_dump(exclude_unset=True)

        from_event_id = values.get("from_event_id", edge.from_event_id)
        to_event_id = values.get("to_event_id", edge.to_event_id)
        self._validate_event_pair(edge.project_id, from_event_id, to_event_id)

        updated = self.edge_repo.update(edge, values)
        self._mark_dirty(edge.project_id, edge_id, "upsert")
        return updated

    def delete_timeline_edge(self, edge_id: str) -> TimelineEdge:
        edge = self.get_timeline_edge(edge_id)
        deleted = self.edge_repo.soft_delete(edge)
        self._mark_dirty(edge.project_id, edge_id, "delete")
        return deleted

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise TimelineEdgeProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark the timeline edge as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "timeline_edges", entity_id, action)
        except Exception:
            pass

    def _validate_event_pair(self, project_id: str, from_event_id: str, to_event_id: str) -> None:
        if from_event_id == to_event_id:
            raise TimelineEdgeSelfReferenceError

        from_event = self.timeline_repo.get_active(from_event_id)
        if from_event is None:
            raise TimelineEdgeEventNotFoundError
        if from_event.project_id != project_id:
            raise TimelineEdgeEventProjectMismatchError

        to_event = self.timeline_repo.get_active(to_event_id)
        if to_event is None:
            raise TimelineEdgeEventNotFoundError
        if to_event.project_id != project_id:
            raise TimelineEdgeEventProjectMismatchError
