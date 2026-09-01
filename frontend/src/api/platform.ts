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
