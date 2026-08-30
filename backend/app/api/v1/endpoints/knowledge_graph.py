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

# ---------------------------------------------------------
# Phase 5.2: Document Entity Extraction & Graph Construction Endpoints
# ---------------------------------------------------------

@router.post("/documents/{document_id}/extract", response_model=dict, dependencies=[Depends(check_rate_limit)])
def extract_document_graph_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extracts entities and constructs knowledge graph representation for the document.
    """
    from app.services.graph_construction import GraphConstructionService
    workspace_id = resolve_workspace_id(current_user, db)
    construction_service = GraphConstructionService(db)
    return construction_service.construct_graph_from_document(
        document_id=document_id,
        user_id=current_user.id,
        workspace_id=workspace_id
    )

@router.get("/documents/{document_id}/entities", response_model=List[NodeResponse], dependencies=[Depends(check_rate_limit)])
def get_document_entities_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all knowledge graph entities associated with the document.
    """
    from app.services.graph_construction import GraphConstructionService
    workspace_id = resolve_workspace_id(current_user, db)
    construction_service = GraphConstructionService(db)
    return construction_service.get_document_entities(
        document_id=document_id,
        user_id=current_user.id,
        workspace_id=workspace_id
    )

@router.get("/documents/{document_id}/relationships", response_model=List[EdgeResponse], dependencies=[Depends(check_rate_limit)])
def get_document_relationships_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all knowledge graph edge relationships for the document.
    """
    from app.services.graph_construction import GraphConstructionService
    workspace_id = resolve_workspace_id(current_user, db)
    construction_service = GraphConstructionService(db)
    return construction_service.get_document_relationships(
        document_id=document_id,
        user_id=current_user.id,
        workspace_id=workspace_id
    )

@router.post("/documents/{document_id}/rebuild", response_model=dict, dependencies=[Depends(check_rate_limit)])
def rebuild_document_graph_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safely rebuilds the knowledge graph nodes and edges for the specified document.
    """
    from app.services.graph_construction import GraphConstructionService
    workspace_id = resolve_workspace_id(current_user, db)
    construction_service = GraphConstructionService(db)
    return construction_service.rebuild_document_graph(
        document_id=document_id,
        user_id=current_user.id,
        workspace_id=workspace_id
    )

# ---------------------------------------------------------
# Memory-Graph Synchronization Endpoints
# ---------------------------------------------------------

@router.post("/sync/memory/{memory_id}", response_model=dict, dependencies=[Depends(check_rate_limit)])
def sync_memory_to_graph_endpoint(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronizes an AgentMemory record into the tenant Knowledge Graph.
    """
    from app.models.memory import AgentMemory
    from app.services.memory_graph_sync import MemoryGraphSyncService
    workspace_id = resolve_workspace_id(current_user, db)

    memory = db.query(AgentMemory).filter(
        AgentMemory.id == memory_id,
        AgentMemory.workspace_id == workspace_id,
        AgentMemory.user_id == current_user.id
    ).first()

    if not memory:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Memory record not found in workspace.")

    sync_service = MemoryGraphSyncService(db)
    return sync_service.sync_memory_to_graph(
        user_id=current_user.id,
        workspace_id=workspace_id,
        memory=memory
    )

@router.post("/nodes/{node_id}/sync-memory", response_model=dict, dependencies=[Depends(check_rate_limit)])
def sync_graph_node_to_memory_endpoint(
    node_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronizes a KnowledgeGraphNode entity into an AgentMemory record.
    """
    from app.services.memory_graph_sync import MemoryGraphSyncService
    workspace_id = resolve_workspace_id(current_user, db)

    sync_service = MemoryGraphSyncService(db)
    mem = sync_service.sync_graph_to_memory(
        user_id=current_user.id,
        workspace_id=workspace_id,
        node_id=node_id
    )
    if not mem:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found or sync skipped to prevent loop.")

    return {
        "status": "synced",
        "memory_id": str(mem.id),
        "content": mem.content,
        "source": mem.source
    }

# ---------------------------------------------------------
# Phase 5.8: Graph Search & Analytics Endpoints
# ---------------------------------------------------------

@router.get("/analytics/overview", response_model=dict, dependencies=[Depends(check_rate_limit)])
def get_graph_analytics_overview_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns high-level graph topology, degree distribution, and provenance analytics.
    """
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    analytics = GraphAnalyticsService(db)
    return analytics.get_analytics_overview(user_id=current_user.id, workspace_id=workspace_id).model_dump()

@router.get("/analytics/health", response_model=dict, dependencies=[Depends(check_rate_limit)])
def get_graph_health_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns graph health diagnostics, orphan rates, and contradiction indicators.
    """
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    analytics = GraphAnalyticsService(db)
    return analytics.get_graph_health(user_id=current_user.id, workspace_id=workspace_id).model_dump()

@router.get("/analytics/top-connected", response_model=List[dict], dependencies=[Depends(check_rate_limit)])
def get_top_connected_entities_endpoint(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the most connected hub nodes in the workspace graph.
    """
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    analytics = GraphAnalyticsService(db)
    items = analytics.get_top_connected_entities(user_id=current_user.id, workspace_id=workspace_id, limit=limit)
    return [i.model_dump() for i in items]

@router.get("/analytics/orphans", response_model=List[dict], dependencies=[Depends(check_rate_limit)])
def get_orphan_nodes_endpoint(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns isolated entities with no connected relationships.
    """
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    analytics = GraphAnalyticsService(db)
    orphans = analytics.get_orphan_nodes(user_id=current_user.id, workspace_id=workspace_id, limit=limit)
    return [o.model_dump() for o in orphans]

@router.get("/analytics/duplicates", response_model=List[dict], dependencies=[Depends(check_rate_limit)])
def get_duplicate_candidates_endpoint(
    similarity_threshold: float = Query(0.85, ge=0.5, le=1.0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns potential duplicate entity pairs for safe review and merging.
    """
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    analytics = GraphAnalyticsService(db)
    candidates = analytics.detect_duplicate_candidates(
        user_id=current_user.id,
        workspace_id=workspace_id,
        similarity_threshold=similarity_threshold,
        limit=limit
    )
    return [c.model_dump() for c in candidates]

@router.post("/search/advanced", response_model=dict, dependencies=[Depends(check_rate_limit)])
def advanced_search_endpoint(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes advanced multi-criterion search with deterministic relevance ranking.
    """
    from app.schemas.knowledge_graph import AdvancedSearchRequest
    from app.services.graph_analytics import GraphAnalyticsService
    workspace_id = resolve_workspace_id(current_user, db)
    req = AdvancedSearchRequest.model_validate(payload)
    analytics = GraphAnalyticsService(db)
    return analytics.advanced_search(user_id=current_user.id, workspace_id=workspace_id, req=req).model_dump()


