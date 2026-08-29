import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.api.v1.endpoints.documents import resolve_workspace_id
from app.services.knowledge_graph import KnowledgeGraphService, NodeNotFound
from app.schemas.knowledge_graph import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    EdgeCreate,
    EdgeResponse,
    NeighborResponse,
    GraphTraversalRequest,
    GraphTraversalResponse,
    GraphContextResponse
)

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])

# ---------------------------------------------------------
# Node Endpoints
# ---------------------------------------------------------

@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
def create_node_endpoint(
    payload: NodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.create_node(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_data=payload
    )

@router.get("/nodes", response_model=List[NodeResponse], dependencies=[Depends(check_rate_limit)])
def list_nodes_endpoint(
    node_type: Optional[str] = Query(None),
    external_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    nodes, _ = service.list_nodes(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_type=node_type,
        external_id=external_id,
        skip=skip,
        limit=limit
    )
    return nodes

@router.get("/nodes/{node_id}", response_model=NodeResponse, dependencies=[Depends(check_rate_limit)])
def get_node_endpoint(
    node_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    node = service.get_node(user_id=current_user.id, workspace_id=workspace_id, node_id=node_id)
    if not node:
        raise NodeNotFound(f"Node {node_id} not found in workspace.")
    return node

@router.patch("/nodes/{node_id}", response_model=NodeResponse, dependencies=[Depends(check_rate_limit)])
def update_node_endpoint(
    node_id: uuid.UUID,
    payload: NodeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.update_node(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_id=node_id,
        update_data=payload
    )

@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_rate_limit)])
def delete_node_endpoint(
    node_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    service.delete_node(user_id=current_user.id, workspace_id=workspace_id, node_id=node_id)
    return None

# ---------------------------------------------------------
# Edge Endpoints
# ---------------------------------------------------------

@router.post("/edges", response_model=EdgeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
def create_edge_endpoint(
    payload: EdgeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.create_edge(
        user_id=current_user.id,
        workspace_id=workspace_id,
        edge_data=payload
    )

@router.get("/edges", response_model=List[EdgeResponse], dependencies=[Depends(check_rate_limit)])
def list_edges_endpoint(
    source_node_id: Optional[uuid.UUID] = Query(None),
    target_node_id: Optional[uuid.UUID] = Query(None),
    relationship_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    edges, _ = service.list_edges(
        user_id=current_user.id,
        workspace_id=workspace_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type=relationship_type,
        skip=skip,
        limit=limit
    )
    return edges

@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_rate_limit)])
def delete_edge_endpoint(
    edge_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    service.delete_edge(user_id=current_user.id, workspace_id=workspace_id, edge_id=edge_id)
    return None

# ---------------------------------------------------------
# Graph Traversal, Neighbors & Search
# ---------------------------------------------------------

@router.get("/nodes/{node_id}/neighbors", response_model=List[NeighborResponse], dependencies=[Depends(check_rate_limit)])
def get_neighbors_endpoint(
    node_id: uuid.UUID,
    relationship_types: Optional[List[str]] = Query(None),
    direction: str = Query("both", pattern="^(both|outgoing|incoming)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.get_neighbors(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_id=node_id,
        relationship_types=relationship_types,
        direction=direction
    )

@router.post("/traverse", response_model=GraphTraversalResponse, dependencies=[Depends(check_rate_limit)])
def traverse_endpoint(
    payload: GraphTraversalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.traverse(
        user_id=current_user.id,
        workspace_id=workspace_id,
        start_node_ids=payload.start_node_ids,
        max_depth=payload.max_depth,
        relationship_types=payload.relationship_types,
        node_types=payload.node_types,
        limit=payload.limit
    )

@router.get("/search", response_model=List[NodeResponse], dependencies=[Depends(check_rate_limit)])
def search_nodes_endpoint(
    q: str = Query(..., min_length=1),
    node_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    return service.search_nodes(
        user_id=current_user.id,
        workspace_id=workspace_id,
        query=q,
        node_type=node_type,
        limit=limit
    )
