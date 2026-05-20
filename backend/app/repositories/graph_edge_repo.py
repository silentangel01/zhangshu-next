from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.graph_edge import GraphEdge


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GraphEdgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        relation_type: str | None = None,
        visibility: str | None = None,
    ) -> list[GraphEdge]:
        statement = select(GraphEdge).where(
            GraphEdge.project_id == project_id,
            GraphEdge.deleted_at.is_(None),
        )

        if relation_type is not None:
            statement = statement.where(GraphEdge.relation_type == relation_type)
        if visibility is not None:
            statement = statement.where(GraphEdge.visibility == visibility)

        statement = statement.order_by(GraphEdge.created_at.asc())
        return list(self.db.scalars(statement).all())

    def list_active_connected_to_node(self, node_id: str) -> list[GraphEdge]:
        statement = select(GraphEdge).where(
            GraphEdge.deleted_at.is_(None),
            or_(GraphEdge.from_node_id == node_id, GraphEdge.to_node_id == node_id),
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, edge_id: str) -> GraphEdge | None:
        statement = select(GraphEdge).where(
            GraphEdge.id == edge_id,
            GraphEdge.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, edge: GraphEdge, *, commit: bool = True) -> GraphEdge:
        self.db.add(edge)
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge

    def update(self, edge: GraphEdge, values: dict[str, object], *, commit: bool = True) -> GraphEdge:
        for field, value in values.items():
            setattr(edge, field, value)

        edge.updated_at = utc_now()
        edge.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge

    def soft_delete(self, edge: GraphEdge, *, commit: bool = True) -> GraphEdge:
        now = utc_now()
        edge.deleted_at = now
        edge.updated_at = now
        edge.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(edge)
        return edge
