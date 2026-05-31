from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode
from app.repositories.character_repo import CharacterRepository
from app.repositories.clue_repo import ClueRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.setting_repo import SettingRepository
from app.repositories.timeline_repo import TimelineRepository
from app.repositories.graph_edge_repo import GraphEdgeRepository
from app.repositories.graph_node_repo import GraphNodeRepository
from app.schemas.graph import GraphEdgeCreate, GraphEdgeUpdate, GraphNodeCreate, GraphNodeUpdate


class GraphProjectNotFoundError(Exception):
    pass


class GraphNodeNotFoundError(Exception):
    pass


class GraphEdgeNotFoundError(Exception):
    pass


class GraphNodeProjectMismatchError(Exception):
    pass


class GraphEdgeSelfReferenceError(Exception):
    pass


class GraphBoundNotFoundError(Exception):
    pass


class GraphBoundProjectMismatchError(Exception):
    pass


class GraphService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.character_repo = CharacterRepository(db)
        self.setting_repo = SettingRepository(db)
        self.clue_repo = ClueRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.node_repo = GraphNodeRepository(db)
        self.edge_repo = GraphEdgeRepository(db)

    def list_project_graph_nodes(
        self,
        project_id: str,
        *,
        node_type: str | None = None,
        bound_type: str | None = None,
        bound_id: str | None = None,
        visibility: str | None = None,
        keyword: str | None = None,
    ) -> list[GraphNode]:
        self._ensure_project_exists(project_id)
        return self.node_repo.list_active_by_project(
            project_id,
            node_type=node_type,
            bound_type=bound_type,
            bound_id=bound_id,
            visibility=visibility,
            keyword=keyword,
        )

    def create_graph_node(self, project_id: str, data: GraphNodeCreate) -> GraphNode:
        self._ensure_project_exists(project_id)
        self._validate_bound_reference(project_id, data.bound_type, data.bound_id)

        node = GraphNode(
            id=str(uuid4()),
            project_id=project_id,
            title=data.title,
            node_type=data.node_type,
            bound_type=data.bound_type,
            bound_id=data.bound_id,
            summary=data.summary,
            x=data.x,
            y=data.y,
            width=data.width,
            height=data.height,
            color=data.color,
            size=data.size,
            visibility=data.visibility,
        )
        created = self.node_repo.create(node)
        self._mark_dirty(project_id, created.id, "graph_nodes", "upsert")
        return created

    def get_graph_node(self, node_id: str) -> GraphNode:
        node = self.node_repo.get_active(node_id)
        if node is None:
            raise GraphNodeNotFoundError
        return node

    def update_graph_node(self, node_id: str, data: GraphNodeUpdate) -> GraphNode:
        node = self.get_graph_node(node_id)
        values = data.model_dump(exclude_unset=True)

        bound_type = values.get("bound_type", node.bound_type)
        bound_id = values.get("bound_id", node.bound_id)
        self._validate_bound_reference(node.project_id, bound_type, bound_id)

        updated = self.node_repo.update(node, values)
        self._mark_dirty(node.project_id, node_id, "graph_nodes", "upsert")
        return updated

    def delete_graph_node(self, node_id: str) -> GraphNode:
        node = self.get_graph_node(node_id)
        connected_edges = self.edge_repo.list_active_connected_to_node(node.id)
        for edge in connected_edges:
            self.edge_repo.soft_delete(edge, commit=False)
            self._mark_dirty(node.project_id, edge.id, "graph_edges", "delete")
        deleted = self.node_repo.soft_delete(node, commit=False)
        self._mark_dirty(node.project_id, node_id, "graph_nodes", "delete")
        self.db.commit()
        self.db.refresh(deleted)
        return deleted

    def list_project_graph_edges(
        self,
        project_id: str,
        *,
        relation_type: str | None = None,
        visibility: str | None = None,
    ) -> list[GraphEdge]:
        self._ensure_project_exists(project_id)
        return self.edge_repo.list_active_by_project(
            project_id,
            relation_type=relation_type,
            visibility=visibility,
        )

    def create_graph_edge(self, project_id: str, data: GraphEdgeCreate) -> GraphEdge:
        self._ensure_project_exists(project_id)
        self._validate_node_pair(project_id, data.from_node_id, data.to_node_id)

        edge = GraphEdge(
            id=str(uuid4()),
            project_id=project_id,
            from_node_id=data.from_node_id,
            to_node_id=data.to_node_id,
            relation_type=data.relation_type,
            direction=data.direction,
            strength=data.strength,
            label=data.label,
            note=data.note,
            line_style=data.line_style,
            visibility=data.visibility,
        )
        created = self.edge_repo.create(edge)
        self._mark_dirty(project_id, created.id, "graph_edges", "upsert")
        return created

    def get_graph_edge(self, edge_id: str) -> GraphEdge:
        edge = self.edge_repo.get_active(edge_id)
        if edge is None:
            raise GraphEdgeNotFoundError
        return edge

    def update_graph_edge(self, edge_id: str, data: GraphEdgeUpdate) -> GraphEdge:
        edge = self.get_graph_edge(edge_id)
        values = data.model_dump(exclude_unset=True)

        from_node_id = values.get("from_node_id", edge.from_node_id)
        to_node_id = values.get("to_node_id", edge.to_node_id)
        self._validate_node_pair(edge.project_id, from_node_id, to_node_id)

        updated = self.edge_repo.update(edge, values)
        self._mark_dirty(edge.project_id, edge_id, "graph_edges", "upsert")
        return updated

    def delete_graph_edge(self, edge_id: str) -> GraphEdge:
        edge = self.get_graph_edge(edge_id)
        deleted = self.edge_repo.soft_delete(edge)
        self._mark_dirty(edge.project_id, edge_id, "graph_edges", "delete")
        return deleted

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise GraphProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, entity_type: str, action: str) -> None:
        """Mark a graph entity as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, entity_type, entity_id, action)
        except Exception:
            pass

    def _validate_bound_reference(
        self,
        project_id: str,
        bound_type: str | None,
        bound_id: str | None,
    ) -> None:
        if bound_type is None or bound_id is None:
            return
        if bound_type == "custom":
            return
        if bound_type == "character":
            bound_object = self.character_repo.get_active(bound_id)
        elif bound_type == "setting":
            bound_object = self.setting_repo.get_active(bound_id)
        elif bound_type == "clue":
            bound_object = self.clue_repo.get_active(bound_id)
        elif bound_type == "timeline_event":
            bound_object = self.timeline_repo.get_active(bound_id)
        else:
            bound_object = None

        if bound_object is None:
            raise GraphBoundNotFoundError
        if bound_object.project_id != project_id:
            raise GraphBoundProjectMismatchError

    def _validate_node_pair(self, project_id: str, from_node_id: str, to_node_id: str) -> None:
        if from_node_id == to_node_id:
            raise GraphEdgeSelfReferenceError

        from_node = self.node_repo.get_active(from_node_id)
        if from_node is None:
            raise GraphNodeNotFoundError
        if from_node.project_id != project_id:
            raise GraphNodeProjectMismatchError

        to_node = self.node_repo.get_active(to_node_id)
        if to_node is None:
            raise GraphNodeNotFoundError
        if to_node.project_id != project_id:
            raise GraphNodeProjectMismatchError
