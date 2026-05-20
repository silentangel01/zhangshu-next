from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.graph import (
    GraphEdgeCreate,
    GraphEdgeRead,
    GraphEdgeRelationType,
    GraphEdgeUpdate,
    GraphNodeBoundType,
    GraphNodeCreate,
    GraphNodeRead,
    GraphNodeType,
    GraphNodeUpdate,
    GraphVisibility,
)
from app.services.graph_service import (
    GraphBoundNotFoundError,
    GraphBoundProjectMismatchError,
    GraphEdgeNotFoundError,
    GraphEdgeSelfReferenceError,
    GraphNodeNotFoundError,
    GraphNodeProjectMismatchError,
    GraphProjectNotFoundError,
    GraphService,
)


router = APIRouter(tags=["graphs"])


def get_graph_service(db: Session = Depends(get_db)) -> GraphService:
    return GraphService(db)


@router.get("/api/projects/{project_id}/graph-nodes", response_model=list[GraphNodeRead])
def list_project_graph_nodes(
    project_id: str,
    node_type: GraphNodeType | None = Query(default=None),
    bound_type: GraphNodeBoundType | None = Query(default=None),
    visibility: GraphVisibility | None = Query(default=None),
    keyword: str | None = Query(default=None),
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.list_project_graph_nodes(
            project_id,
            node_type=node_type,
            bound_type=bound_type,
            visibility=visibility,
            keyword=keyword,
        )
    except GraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/graph-nodes",
    response_model=GraphNodeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_graph_node(
    project_id: str,
    data: GraphNodeCreate,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.create_graph_node(project_id, data)
    except GraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except GraphBoundNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Bound object not found") from exc
    except GraphBoundProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Bound object does not belong to project") from exc


@router.get("/api/graph-nodes/{node_id}", response_model=GraphNodeRead)
def get_graph_node(
    node_id: str,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.get_graph_node(node_id)
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph node not found") from exc


@router.patch("/api/graph-nodes/{node_id}", response_model=GraphNodeRead)
def update_graph_node(
    node_id: str,
    data: GraphNodeUpdate,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.update_graph_node(node_id, data)
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph node not found") from exc
    except GraphBoundNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Bound object not found") from exc
    except GraphBoundProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Bound object does not belong to project") from exc


@router.delete("/api/graph-nodes/{node_id}", response_model=GraphNodeRead)
def delete_graph_node(
    node_id: str,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.delete_graph_node(node_id)
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph node not found") from exc


@router.get("/api/projects/{project_id}/graph-edges", response_model=list[GraphEdgeRead])
def list_project_graph_edges(
    project_id: str,
    relation_type: GraphEdgeRelationType | None = Query(default=None),
    visibility: GraphVisibility | None = Query(default=None),
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.list_project_graph_edges(
            project_id,
            relation_type=relation_type,
            visibility=visibility,
        )
    except GraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/graph-edges",
    response_model=GraphEdgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_graph_edge(
    project_id: str,
    data: GraphEdgeCreate,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.create_graph_edge(project_id, data)
    except GraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph node not found") from exc
    except GraphNodeProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Graph node does not belong to project") from exc
    except GraphEdgeSelfReferenceError as exc:
        raise HTTPException(status_code=400, detail="Graph edge cannot connect a node to itself") from exc


@router.get("/api/graph-edges/{edge_id}", response_model=GraphEdgeRead)
def get_graph_edge(
    edge_id: str,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.get_graph_edge(edge_id)
    except GraphEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph edge not found") from exc


@router.patch("/api/graph-edges/{edge_id}", response_model=GraphEdgeRead)
def update_graph_edge(
    edge_id: str,
    data: GraphEdgeUpdate,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.update_graph_edge(edge_id, data)
    except GraphEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph edge not found") from exc
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph node not found") from exc
    except GraphNodeProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Graph node does not belong to project") from exc
    except GraphEdgeSelfReferenceError as exc:
        raise HTTPException(status_code=400, detail="Graph edge cannot connect a node to itself") from exc


@router.delete("/api/graph-edges/{edge_id}", response_model=GraphEdgeRead)
def delete_graph_edge(
    edge_id: str,
    service: GraphService = Depends(get_graph_service),
):
    try:
        return service.delete_graph_edge(edge_id)
    except GraphEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Graph edge not found") from exc
