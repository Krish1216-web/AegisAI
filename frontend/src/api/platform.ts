import { request } from './client';

export interface PlatformStatus {
  version: string;
  phase: string;
  workspace_id: string;
  active_capabilities: number;
  system_health: string;
  feature_flags: Record<string, boolean>;
  registered_subsystems: string[];
}

export interface PlatformCapability {
  capability_id: string;
  capability_type: 'agent' | 'rag' | 'knowledge_graph' | 'memory' | 'mcp' | 'workflow' | 'external_service' | 'intelligence' | 'reasoning';
  name: string;
  description: string;
  version: string;
  enabled: boolean;
  workspace_scope?: string | null;
  required_permissions: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  tags: string[];
  metadata: Record<string, any>;
}

export interface PlatformCapabilityListResponse {
  total: number;
  items: PlatformCapability[];
  workspace_id: string;
}

export interface PlatformExecutionRequest {
  capability_id: string;
  input_data?: Record<string, any>;
  idempotency_key?: string;
  timeout_seconds?: number;
  metadata?: Record<string, any>;
}

export interface PlatformExecutionResult {
  execution_id: string;
  capability_id: string;
  status: 'requested' | 'validating' | 'planned' | 'executing' | 'verifying' | 'completed' | 'failed' | 'cancelled' | 'denied' | 'waiting';
  output: Record<string, any>;
  provenance: Array<{
    id: string;
    source_type: string;
    source_id: string;
    title?: string;
    trust_level: string;
    workspace_id: string;
    confidence?: number;
    snippet?: string;
    metadata?: Record<string, any>;
  }>;
  warnings: string[];
  errors: Array<{ code: string; message: string }>;
  started_at: string;
  completed_at?: string | null;
  duration_ms: number;
  correlation_id: string;
  metadata: Record<string, any>;
}

export async function getPlatformStatus(): Promise<PlatformStatus> {
  return request<PlatformStatus>('/platform/status');
}

export async function getPlatformCapabilities(capabilityType?: string): Promise<PlatformCapabilityListResponse> {
  const query = capabilityType ? `?capability_type=${encodeURIComponent(capabilityType)}` : '';
  return request<PlatformCapabilityListResponse>(`/platform/capabilities${query}`);
}

export async function getPlatformCapability(capabilityId: string): Promise<{ capability: PlatformCapability }> {
  return request<{ capability: PlatformCapability }>(`/platform/capabilities/${encodeURIComponent(capabilityId)}`);
}

export async function executePlatformCapability(payload: PlatformExecutionRequest): Promise<PlatformExecutionResult> {
  return request<PlatformExecutionResult>('/platform/execute', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function getPlatformExecution(executionId: string): Promise<PlatformExecutionResult> {
  return request<PlatformExecutionResult>(`/platform/executions/${encodeURIComponent(executionId)}`);
}

export async function cancelPlatformExecution(executionId: string, reason?: string): Promise<PlatformExecutionResult> {
  return request<PlatformExecutionResult>(`/platform/executions/${encodeURIComponent(executionId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

