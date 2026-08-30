import { request } from './client';

export interface KnowledgeGraphNode {
  id: string;
  user_id: string;
  workspace_id: string;
  node_type: string;
  external_id?: string | null;
  name: string;
  description?: string | null;
  metadata?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeGraphEdge {
  id: string;
  user_id: string;
  workspace_id: string;
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  confidence: number;
  properties?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface NeighborItem {
  node: KnowledgeGraphNode;
  relationship_type: string;
  direction: 'outgoing' | 'incoming';
  confidence: number;
  edge_id: string;
}

export interface RelatedEntityItem {
  node_id: string;
  node_type: string;
  name: string;
  description?: string | null;
  distance: number;
  relevance_score: number;
  relationship_path: string[];
  metadata?: Record<string, any> | null;
}

export interface RelatedEntitiesResponse {
  node_id: string;
  depth: number;
  total_related: number;
  related_entities: RelatedEntityItem[];
}

export interface GraphPathStep {
  from_node_id: string;
  from_node_name: string;
  to_node_id: string;
  to_node_name: string;
  relationship_type: string;
  direction: 'outgoing' | 'incoming';
  confidence: number;
}

export interface GraphPathResponse {
  source_node_id: string;
  target_node_id: string;
  path_found: boolean;
  distance: number;
  steps: GraphPathStep[];
  nodes: KnowledgeGraphNode[];
}

export interface RelationshipDetail {
  relationship_type: string;
  direction: 'outgoing' | 'incoming' | 'bidirectional';
  confidence: number;
  distance: number;
  via_nodes: string[];
}

export interface RelationshipAnalysisResponse {
  source_node: KnowledgeGraphNode;
  target_node: KnowledgeGraphNode;
  are_connected: boolean;
  min_distance?: number | null;
  direct_relationships: RelationshipDetail[];
  indirect_relationships: RelationshipDetail[];
  summary: string;
}

export interface GraphContextResponse {
  entities: any[];
  relationships: any[];
  formatted_context: string;
}

export interface GraphTraversalResponse {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  depth_reached: number;
  total_nodes: number;
  total_edges: number;
}

// ----------------------------------------------------------------------
// Core API Calls
// ----------------------------------------------------------------------

export async function listNodes(params?: {
  node_type?: string;
  external_id?: string;
  skip?: number;
  limit?: number;
}): Promise<KnowledgeGraphNode[]> {
  const query = new URLSearchParams();
  if (params?.node_type) query.append('node_type', params.node_type);
  if (params?.external_id) query.append('external_id', params.external_id);
  if (params?.skip !== undefined) query.append('skip', String(params.skip));
  if (params?.limit !== undefined) query.append('limit', String(params.limit));

  const qs = query.toString();
  return request<KnowledgeGraphNode[]>(`/knowledge-graph/nodes${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

export async function getNode(nodeId: string): Promise<KnowledgeGraphNode> {
  return request<KnowledgeGraphNode>(`/knowledge-graph/nodes/${nodeId}`, {
    method: 'GET',
  });
}

export async function createNode(payload: {
  node_type: string;
  name: string;
  external_id?: string;
  description?: string;
  metadata?: Record<string, any>;
}): Promise<KnowledgeGraphNode> {
  return request<KnowledgeGraphNode>('/knowledge-graph/nodes', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteNode(nodeId: string): Promise<void> {
  return request<void>(`/knowledge-graph/nodes/${nodeId}`, {
    method: 'DELETE',
  });
}

export async function listEdges(params?: {
  relationship_type?: string;
  source_node_id?: string;
  target_node_id?: string;
  skip?: number;
  limit?: number;
}): Promise<KnowledgeGraphEdge[]> {
  const query = new URLSearchParams();
  if (params?.relationship_type) query.append('relationship_type', params.relationship_type);
  if (params?.source_node_id) query.append('source_node_id', params.source_node_id);
  if (params?.target_node_id) query.append('target_node_id', params.target_node_id);
  if (params?.skip !== undefined) query.append('skip', String(params.skip));
  if (params?.limit !== undefined) query.append('limit', String(params.limit));

  const qs = query.toString();
  return request<KnowledgeGraphEdge[]>(`/knowledge-graph/edges${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

export async function createEdge(payload: {
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  confidence?: number;
  properties?: Record<string, any>;
}): Promise<KnowledgeGraphEdge> {
  return request<KnowledgeGraphEdge>('/knowledge-graph/edges', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteEdge(edgeId: string): Promise<void> {
  return request<void>(`/knowledge-graph/edges/${edgeId}`, {
    method: 'DELETE',
  });
}

export async function getNeighbors(
  nodeId: string,
  params?: { relationship_types?: string[]; direction?: string }
): Promise<NeighborItem[]> {
  const query = new URLSearchParams();
  if (params?.direction) query.append('direction', params.direction);
  if (params?.relationship_types) {
    params.relationship_types.forEach((r) => query.append('relationship_types', r));
  }

  const qs = query.toString();
  return request<NeighborItem[]>(`/knowledge-graph/nodes/${nodeId}/neighbors${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

export async function getRelatedEntities(
  nodeId: string,
  params?: {
    depth?: number;
    limit?: number;
    relationship_types?: string[];
    node_types?: string[];
  }
): Promise<RelatedEntitiesResponse> {
  const query = new URLSearchParams();
  if (params?.depth !== undefined) query.append('depth', String(params.depth));
  if (params?.limit !== undefined) query.append('limit', String(params.limit));
  if (params?.relationship_types) {
    params.relationship_types.forEach((r) => query.append('relationship_types', r));
  }
  if (params?.node_types) {
    params.node_types.forEach((nt) => query.append('node_types', nt));
  }

  const qs = query.toString();
  return request<RelatedEntitiesResponse>(`/knowledge-graph/nodes/${nodeId}/related${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

export async function searchNodes(query: string, nodeType?: string, limit: number = 20): Promise<KnowledgeGraphNode[]> {
  const q = new URLSearchParams({ q: query, limit: String(limit) });
  if (nodeType) q.append('node_type', nodeType);
  return request<KnowledgeGraphNode[]>(`/knowledge-graph/search?${q.toString()}`, {
    method: 'GET',
  });
}

export async function searchEnhanced(params: {
  q?: string;
  node_type?: string;
  relationship_type?: string;
  depth?: number;
  limit?: number;
}): Promise<RelatedEntityItem[]> {
  const query = new URLSearchParams();
  if (params.q) query.append('q', params.q);
  if (params.node_type) query.append('node_type', params.node_type);
  if (params.relationship_type) query.append('relationship_type', params.relationship_type);
  if (params.depth !== undefined) query.append('depth', String(params.depth));
  if (params.limit !== undefined) query.append('limit', String(params.limit));

  const qs = query.toString();
  return request<RelatedEntityItem[]>(`/knowledge-graph/search/enhanced${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

export async function findPath(payload: {
  source_node_id: string;
  target_node_id: string;
  max_depth?: number;
  allowed_relationship_types?: string[];
}): Promise<GraphPathResponse> {
  return request<GraphPathResponse>('/knowledge-graph/path', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function analyzeRelationships(payload: {
  source_node_id: string;
  target_node_id: string;
  max_depth?: number;
}): Promise<RelationshipAnalysisResponse> {
  return request<RelationshipAnalysisResponse>('/knowledge-graph/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getGraphContext(payload: {
  entity_names?: string[];
  node_ids?: string[];
  depth?: number;
  max_entities?: number;
}): Promise<GraphContextResponse> {
  return request<GraphContextResponse>('/knowledge-graph/context', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ----------------------------------------------------------------------
// Document Graph API Calls
// ----------------------------------------------------------------------

export async function extractDocumentGraph(documentId: string): Promise<Record<string, any>> {
  return request<Record<string, any>>(`/knowledge-graph/documents/${documentId}/extract`, {
    method: 'POST',
  });
}

export async function getDocumentEntities(documentId: string): Promise<KnowledgeGraphNode[]> {
  return request<KnowledgeGraphNode[]>(`/knowledge-graph/documents/${documentId}/entities`, {
    method: 'GET',
  });
}

export async function getDocumentRelationships(documentId: string): Promise<KnowledgeGraphEdge[]> {
  return request<KnowledgeGraphEdge[]>(`/knowledge-graph/documents/${documentId}/relationships`, {
    method: 'GET',
  });
}

export async function rebuildDocumentGraph(documentId: string): Promise<Record<string, any>> {
  return request<Record<string, any>>(`/knowledge-graph/documents/${documentId}/rebuild`, {
    method: 'POST',
  });
}

// ----------------------------------------------------------------------
// Memory-Graph Synchronization API Calls
// ----------------------------------------------------------------------

export async function syncMemoryToGraph(memoryId: string): Promise<Record<string, any>> {
  return request<Record<string, any>>(`/knowledge-graph/sync/memory/${memoryId}`, {
    method: 'POST',
  });
}

export async function syncGraphNodeToMemory(nodeId: string): Promise<Record<string, any>> {
  return request<Record<string, any>>(`/knowledge-graph/nodes/${nodeId}/sync-memory`, {
    method: 'POST',
  });
}

