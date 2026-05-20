from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timeline_edge import TimelineEdge


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineEdgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        edge_type: str | None = None,
        visibility: str | None = None,
    ) -> list[TimelineEdge]:
        statement = select(TimelineEdge).where(
            TimelineEdge.project_id == project_id,
            TimelineEdge.deleted_at.is_(None),
        )

        if edge_type is not None:
            statement = statement.where(TimelineEdge.edge_type == edge_type)
        if visibility is not None:
            statement = statement.where(TimelineEdge.visibility == visibility)

        statement = statement.order_by(TimelineEdge.created_at.asc())
        return list(self.db.scalars(statement).all())

    def get_active(self, edge_id: str) -> TimelineEdge | None:
        statement = select(TimelineEdge).where(
            TimelineEdge.id == edge_id,
            TimelineEdge.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, edge: TimelineEdge, *, commit: bool = True) -> TimelineEdge:
        self.db.add(edge)
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge

    def update(self, edge: TimelineEdge, values: dict[str, object], *, commit: bool = True) -> TimelineEdge:
        for field, value in values.items():
            setattr(edge, field, value)

        edge.updated_at = utc_now()
        edge.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge

    def soft_delete(self, edge: TimelineEdge, *, commit: bool = True) -> TimelineEdge:
        now = utc_now()
        edge.deleted_at = now
        edge.updated_at = now
        edge.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge
