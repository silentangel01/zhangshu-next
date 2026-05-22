from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.graph_node import GraphNode


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GraphNodeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        node_type: str | None = None,
        bound_type: str | None = None,
        bound_id: str | None = None,
        visibility: str | None = None,
        keyword: str | None = None,
    ) -> list[GraphNode]:
        statement = select(GraphNode).where(
            GraphNode.project_id == project_id,
            GraphNode.deleted_at.is_(None),
        )

        if node_type is not None:
            statement = statement.where(GraphNode.node_type == node_type)
        if bound_type is not None:
            statement = statement.where(GraphNode.bound_type == bound_type)
        if bound_id is not None:
            statement = statement.where(GraphNode.bound_id == bound_id)
        if visibility is not None:
            statement = statement.where(GraphNode.visibility == visibility)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    GraphNode.title.ilike(pattern),
                    GraphNode.summary.ilike(pattern),
                )
            )

        statement = statement.order_by(GraphNode.updated_at.desc(), GraphNode.created_at.desc())
        return list(self.db.scalars(statement).all())

    def get_active(self, node_id: str) -> GraphNode | None:
        statement = select(GraphNode).where(
            GraphNode.id == node_id,
            GraphNode.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, node: GraphNode, *, commit: bool = True) -> GraphNode:
        self.db.add(node)
        if commit:
            self.db.commit()
            self.db.refresh(node)
        return node

    def update(self, node: GraphNode, values: dict[str, object], *, commit: bool = True) -> GraphNode:
        for field, value in values.items():
            setattr(node, field, value)

        node.updated_at = utc_now()
        node.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(node)
        return node

    def soft_delete(self, node: GraphNode, *, commit: bool = True) -> GraphNode:
        now = utc_now()
        node.deleted_at = now
        node.updated_at = now
        node.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(node)
        return node
