import { request } from './client';

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_title?: string;
  content: string;
  similarity_score: number;
  rerank_score?: number;
  metadata?: Record<string, any>;
}

export interface Citation {
  citation_number: number;
  chunk_id: string;
  document_id: string;
  document_title?: string;
  snippet: string;
}

export interface RAGResponse {
  query: string;
  answer: string;
  retrieved_chunks: RetrievedChunk[];
  citations: Citation[];
  processing_time_ms: number;
  no_evidence_found?: boolean;
}

export interface HybridRAGResponse {
  query: string;
  answer: string;
  vector_chunks: RetrievedChunk[];
  graph_entities: Array<{
    node_id: string;
    name: string;
    node_type: string;
    relevance_score?: number;
  }>;
  graph_relationships: Array<{
    source: string;
    target: string;
    relationship_type: string;
    confidence?: number;
  }>;
  citations: Citation[];
  processing_time_ms: number;
  no_evidence_found?: boolean;
}

export interface RAGQueryRecord {
  id: string;
  query_text: string;
  answer_text: string;
  processing_time_ms: number;
  created_at: string;
}

/**
 * Standard Vector RAG query
 */
export async function queryRAG(payload: {
  query: string;
  limit?: number;
  similarity_threshold?: number;
  rerank?: boolean;
}): Promise<RAGResponse> {
  return request<RAGResponse>('/rag/query', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Hybrid Vector + Graph RAG query
 */
export async function queryHybridRAG(payload: {
  query: string;
  top_k?: number;
  graph_depth?: number;
  similarity_threshold?: number;
}): Promise<HybridRAGResponse> {
  return request<HybridRAGResponse>('/rag/hybrid/query', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Lists previous RAG query history
 */
export async function getRAGQueries(limit: number = 20, offset: number = 0): Promise<RAGQueryRecord[]> {
  return request<RAGQueryRecord[]>(`/rag/queries?limit=${limit}&offset=${offset}`, {
    method: 'GET'
  }).catch(() => []);
}

/**
 * Retrieves citations for a specific RAG query
 */
export async function getRAGQueryCitations(queryId: string): Promise<Citation[]> {
  return request<Citation[]>(`/rag/queries/${queryId}/citations`, {
    method: 'GET'
  }).catch(() => []);
}
