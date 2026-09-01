import api from './client';

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
  const response = await api.get('/platform/status');
  return response.data;
}

export async function getPlatformCapabilities(capabilityType?: string): Promise<PlatformCapabilityListResponse> {
  const params: Record<string, any> = {};
  if (capabilityType) {
    params.capability_type = capabilityType;
  }
  const response = await api.get('/platform/capabilities', { params });
  return response.data;
}

export async function getPlatformCapability(capabilityId: string): Promise<{ capability: PlatformCapability }> {
  const response = await api.get(`/platform/capabilities/${encodeURIComponent(capabilityId)}`);
  return response.data;
}

export async function executePlatformCapability(request: PlatformExecutionRequest): Promise<PlatformExecutionResult> {
  const response = await api.post('/platform/execute', request);
  return response.data;
}

export async function getPlatformExecution(executionId: string): Promise<PlatformExecutionResult> {
  const response = await api.get(`/platform/executions/${encodeURIComponent(executionId)}`);
  return response.data;
}

export async function cancelPlatformExecution(executionId: string, reason?: string): Promise<PlatformExecutionResult> {
  const response = await api.post(`/platform/executions/${encodeURIComponent(executionId)}/cancel`, { reason });
  return response.data;
}
