import { request } from './client';
import { syncMemoryToGraph as syncMemoryToGraphAPI } from './knowledgeGraph';

export type MemoryType =
  | 'USER_PREFERENCE'
  | 'USER_FACT'
  | 'PROJECT_CONTEXT'
  | 'TASK_HISTORY'
  | 'DOCUMENT_CONTEXT'
  | 'LEARNING'
  | 'SYSTEM_KNOWLEDGE'
  | 'CONVERSATION'
  | 'SESSION';

export interface MemoryRecord {
  id: string;
  workspace_id: string;
  user_id: string;
  memory_type: MemoryType;
  content: string;
  source: string;
  importance: number;
  confidence: number;
  tags: string[];
  meta_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  graph_synced?: boolean;
  linked_entities?: Array<{ name: string; type: string }>;
  agent_access?: string[];
}

export interface MemoryHealthStatus {
  service: 'HEALTHY' | 'DEGRADED' | 'OFFLINE';
  vector_engine: string;
  graph_sync_enabled: boolean;
  tenant_isolation: string;
  total_memories: number;
  last_sync?: string;
}

// Canonical default memories for workspace initialization
export const CANONICAL_WORKSPACE_MEMORIES: MemoryRecord[] = [
  {
    id: 'mem-vec-001',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'USER_PREFERENCE',
    content: 'Operator prefers FastAPI asynchronous endpoints with Pydantic v2 schemas and Vite + React frontend architectures.',
    source: 'operator_preference',
    importance: 0.95,
    confidence: 0.98,
    tags: ['fastapi', 'python', 'react', 'frontend'],
    meta_data: {
      sync_origin: 'manual_declaration',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-01T10:14:00Z',
    updated_at: '2026-10-05T14:30:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'FastAPI', type: 'SKILL' },
      { name: 'React', type: 'SKILL' }
    ],
    agent_access: ['Memory Agent', 'Orchestrator Agent', 'Response Generator Agent']
  },
  {
    id: 'mem-vec-002',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'USER_FACT',
    content: 'Active workspace uses PostgreSQL 16 with pgvector extension enabled for 1536-dimensional semantic vector indexing.',
    source: 'environment_discovery',
    importance: 0.90,
    confidence: 0.96,
    tags: ['postgresql', 'pgvector', 'database', 'infrastructure'],
    meta_data: {
      sync_origin: 'system_introspection',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-02T11:20:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'PostgreSQL', type: 'DATABASE' },
      { name: 'pgvector', type: 'EXTENSION' }
    ],
    agent_access: ['Memory Agent', 'Enterprise RAG Agent', 'Tool Executor Agent']
  },
  {
    id: 'mem-vec-003',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'PROJECT_CONTEXT',
    content: 'AegisAI autonomous multi-agent system uses LangGraph-inspired DAG orchestration across 9 canonical system agents.',
    source: 'architecture_dossier',
    importance: 0.98,
    confidence: 0.99,
    tags: ['architecture', 'dag', 'orchestrator', 'agents'],
    meta_data: {
      sync_origin: 'architecture_spec',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-02T15:45:00Z',
    updated_at: '2026-10-05T16:10:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'AegisAI', type: 'PROJECT' },
      { name: 'Orchestrator', type: 'AGENT' }
    ],
    agent_access: ['Orchestrator Agent', 'Planner Agent', 'Critic & Consensus Agent']
  },
  {
    id: 'mem-vec-004',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'TASK_HISTORY',
    content: 'Executed hybrid vector and knowledge graph query analysis with multi-hop entity traversal and citation grounding.',
    source: 'agent_execution',
    importance: 0.85,
    confidence: 0.92,
    tags: ['rag', 'hybrid_rag', 'knowledge_graph', 'traversal'],
    meta_data: {
      sync_origin: 'execution_result',
      execution_id: 'exec-88219-rag',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-03T09:12:00Z',
    updated_at: '2026-10-04T18:22:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'Knowledge Graph', type: 'SUBSYSTEM' },
      { name: 'Hybrid RAG', type: 'CAPABILITY' }
    ],
    agent_access: ['Enterprise RAG Agent', 'Graph Reasoning Agent', 'Critic & Consensus Agent']
  },
  {
    id: 'mem-vec-005',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'DOCUMENT_CONTEXT',
    content: 'Enterprise security documentation mandates strict tenant isolation, RBAC role-gated endpoints, and PII secret scrubbing.',
    source: 'document_ingestion',
    importance: 0.92,
    confidence: 0.97,
    tags: ['security', 'tenant_isolation', 'rbac', 'compliance'],
    meta_data: {
      sync_origin: 'document_rag',
      document_id: 'doc-sec-policy-2026',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-03T14:30:00Z',
    updated_at: '2026-10-04T19:00:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'Tenant Isolation', type: 'POLICY' },
      { name: 'RBAC', type: 'SECURITY' }
    ],
    agent_access: ['Memory Agent', 'Orchestrator Agent', 'Tool Executor Agent']
  },
  {
    id: 'mem-vec-006',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'LEARNING',
    content: 'Critic & Consensus agent enforces minimum 0.80 verification threshold before response generator delivers final output.',
    source: 'agent_reflection',
    importance: 0.88,
    confidence: 0.94,
    tags: ['critic', 'consensus', 'verification', 'threshold'],
    meta_data: {
      sync_origin: 'reflection_loop',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-04T08:45:00Z',
    updated_at: '2026-10-05T09:15:00Z',
    graph_synced: false,
    linked_entities: [
      { name: 'Critic Consensus', type: 'AGENT' }
    ],
    agent_access: ['Critic & Consensus Agent', 'Response Generator Agent']
  },
  {
    id: 'mem-vec-007',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'SYSTEM_KNOWLEDGE',
    content: 'Model Context Protocol (MCP) tool servers run in sandboxed subprocesses with JSON-RPC 2.0 stdio / SSE transport.',
    source: 'platform_kernel',
    importance: 0.96,
    confidence: 0.99,
    tags: ['mcp', 'tools', 'sandbox', 'jsonrpc'],
    meta_data: {
      sync_origin: 'kernel_definition',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-04T16:00:00Z',
    updated_at: '2026-10-05T11:45:00Z',
    graph_synced: true,
    linked_entities: [
      { name: 'MCP Protocol', type: 'STANDARD' },
      { name: 'Tool Sandbox', type: 'SECURITY' }
    ],
    agent_access: ['Tool Executor Agent', 'Orchestrator Agent']
  },
  {
    id: 'mem-vec-008',
    workspace_id: 'ws-prod-01',
    user_id: 'usr-admin-01',
    memory_type: 'SESSION',
    content: 'Current workspace operator session initialized with ADMIN privileges across AI OS subsystems.',
    source: 'session_auth',
    importance: 0.70,
    confidence: 0.90,
    tags: ['session', 'auth', 'admin', 'workspace'],
    meta_data: {
      sync_origin: 'session_lifecycle',
      embedding_dim: 1536,
      scrubbed: true
    },
    created_at: '2026-10-05T18:00:00Z',
    updated_at: '2026-10-05T18:00:00Z',
    graph_synced: false,
    linked_entities: [
      { name: 'Operator Session', type: 'USER' }
    ],
    agent_access: ['Memory Agent', 'Orchestrator Agent']
  }
];

export async function triggerMemoryGraphSync(memoryId: string): Promise<Record<string, any>> {
  return syncMemoryToGraphAPI(memoryId);
}
