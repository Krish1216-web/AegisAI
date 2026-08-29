import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.api.v1.endpoints.documents import resolve_workspace_id
from app.services.knowledge_graph import KnowledgeGraphService, NodeNotFound, EdgeNotFound
from app.services.knowledge_graph_intelligence import KnowledgeGraphIntelligenceService
from app.schemas.knowledge_graph import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    EdgeCreate,
    EdgeResponse,
    NeighborResponse,
    GraphTraversalRequest,
    GraphTraversalResponse,
    GraphContextResponse,
    RelatedEntitiesResponse,
    PathSearchRequest,
    GraphPathResponse,
    RelationshipAnalysisRequest,
    RelationshipAnalysisResponse,
    GraphIntelligenceContextRequest,
    RelatedEntityItem
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
    relationship_type: Optional[str] = Query(None),
    source_node_id: Optional[uuid.UUID] = Query(None),
    target_node_id: Optional[uuid.UUID] = Query(None),
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
        relationship_type=relationship_type,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        skip=skip,
        limit=limit
    )
    return edges

@router.get("/edges/{edge_id}", response_model=EdgeResponse, dependencies=[Depends(check_rate_limit)])
def get_edge_endpoint(
    edge_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    service = KnowledgeGraphService(db)
    edge = service.get_edge(user_id=current_user.id, workspace_id=workspace_id, edge_id=edge_id)
    if not edge:
        raise EdgeNotFound(f"Edge {edge_id} not found in workspace.")
    return edge

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
# Graph Traversal, Neighbors & Basic Search
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

# ---------------------------------------------------------
# Phase 5.1: Graph Intelligence Endpoints
# ---------------------------------------------------------

@router.get("/nodes/{node_id}/related", response_model=RelatedEntitiesResponse, dependencies=[Depends(check_rate_limit)])
def get_related_entities_endpoint(
    node_id: uuid.UUID,
    depth: int = Query(2, ge=1, le=5),
    limit: int = Query(50, ge=1, le=500),
    relationship_types: Optional[List[str]] = Query(None),
    node_types: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    intelligence_service = KnowledgeGraphIntelligenceService(db)
    return intelligence_service.get_related_entities(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_id=node_id,
        depth=depth,
        limit=limit,
        relationship_types=relationship_types,
        node_types=node_types
    )

@router.post("/path", response_model=GraphPathResponse, dependencies=[Depends(check_rate_limit)])
def find_shortest_path_endpoint(
    payload: PathSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    intelligence_service = KnowledgeGraphIntelligenceService(db)
    return intelligence_service.find_shortest_path(
        user_id=current_user.id,
        workspace_id=workspace_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        max_depth=payload.max_depth,
        allowed_relationship_types=payload.allowed_relationship_types
    )

@router.post("/analyze", response_model=RelationshipAnalysisResponse, dependencies=[Depends(check_rate_limit)])
def analyze_relationships_endpoint(
    payload: RelationshipAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    intelligence_service = KnowledgeGraphIntelligenceService(db)
    return intelligence_service.analyze_relationships(
        user_id=current_user.id,
        workspace_id=workspace_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        max_depth=payload.max_depth
    )

@router.post("/context", response_model=GraphContextResponse, dependencies=[Depends(check_rate_limit)])
def get_graph_context_endpoint(
    payload: GraphIntelligenceContextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    intelligence_service = KnowledgeGraphIntelligenceService(db)
    formatted = intelligence_service.build_graph_context(
        user_id=current_user.id,
        workspace_id=workspace_id,
        entity_names=payload.entity_names,
        node_ids=payload.node_ids,
        depth=payload.depth,
        max_entities=payload.max_entities
    )
    return GraphContextResponse(
        entities=[],
        relationships=[],
        formatted_context=formatted
    )

@router.get("/search/enhanced", response_model=List[RelatedEntityItem], dependencies=[Depends(check_rate_limit)])
def enhanced_graph_search_endpoint(
    q: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None),
    relationship_type: Optional[str] = Query(None),
    depth: int = Query(1, ge=0, le=3),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user, db)
    intelligence_service = KnowledgeGraphIntelligenceService(db)
    return intelligence_service.enhanced_graph_search(
        user_id=current_user.id,
        workspace_id=workspace_id,
        query=q,
        node_type=node_type,
        relationship_type=relationship_type,
        depth=depth,
        limit=limit
    )
