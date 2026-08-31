export type MCPTransport = 'sse' | 'streamable_http' | 'stdio';
export type MCPServerStatus = 'active' | 'inactive' | 'error' | 'disabled';
export type MCPCapabilityType = 'tool' | 'resource' | 'prompt';
export type MCPAuthenticationType = 'none' | 'api_key' | 'bearer' | 'oauth';

export interface MCPServer {
  id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  description?: string;
  server_url: string;
  transport: MCPTransport;
  status: MCPServerStatus;
  enabled: boolean;
  authentication_type: MCPAuthenticationType;
  auth_config?: Record<string, any>;
  metadata?: Record<string, any>;
  server_version?: string;
  protocol_version?: string;
  last_connected_at?: string;
  last_health_check_at?: string;
  last_discovery_at?: string;
  last_error?: string;
  capabilities_count: number;
  created_at: string;
  updated_at: string;
}

export interface MCPCapability {
  id: string;
  server_id: string;
  capability_type: MCPCapabilityType;
  name: string;
  description?: string;
  input_schema?: Record<string, any>;
  metadata?: Record<string, any>;
  enabled: boolean;
  definition_hash?: string;
  is_stale: boolean;
  stale_at?: string;
  first_discovered_at?: string;
  last_discovered_at?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface MCPDiscoveryResult {
  server_id: string;
  server_name: string;
  status: string;
  server_version?: string;
  protocol_version?: string;
  total_tools: number;
  total_resources: number;
  total_prompts: number;
  tools_added: number;
  tools_changed: number;
  resources_added: number;
  resources_changed: number;
  prompts_added: number;
  prompts_changed: number;
  stale_capabilities: number;
  reactivated_capabilities: number;
  unchanged_capabilities: number;
  discovered_at: string;
  discovery_latency_ms: number;
}

export interface MCPHealthCheckResult {
  server_id: string;
  server_name: string;
  status: string;
  is_healthy: boolean;
  latency_ms?: number;
  last_health_check_at: string;
  server_version?: string;
  protocol_version?: string;
  error?: string;
}

const API_BASE = '/api/v1/mcp';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || 'An error occurred during MCP request');
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export async function listMCPServers(params?: {
  status?: MCPServerStatus;
  enabled_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ servers: MCPServer[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.enabled_only) query.append('enabled_only', 'true');
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset) query.append('offset', params.offset.toString());

  const qs = query.toString();
  return request(`/servers${qs ? `?${qs}` : ''}`);
}

export async function getMCPServer(serverId: string): Promise<MCPServer> {
  return request(`/servers/${serverId}`);
}

export async function registerMCPServer(payload: {
  name: string;
  server_url: string;
  transport?: MCPTransport;
  description?: string;
  authentication_type?: MCPAuthenticationType;
  auth_config?: Record<string, any>;
  metadata?: Record<string, any>;
}): Promise<MCPServer> {
  return request('/servers', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateMCPServer(
  serverId: string,
  payload: {
    name?: string;
    description?: string;
    server_url?: string;
    transport?: MCPTransport;
    authentication_type?: MCPAuthenticationType;
    auth_config?: Record<string, any>;
    metadata?: Record<string, any>;
    enabled?: boolean;
  }
): Promise<MCPServer> {
  return request(`/servers/${serverId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteMCPServer(serverId: string): Promise<void> {
  return request(`/servers/${serverId}`, {
    method: 'DELETE',
  });
}

export async function discoverServerCapabilities(
  serverId: string,
  forceRefresh: boolean = false
): Promise<MCPDiscoveryResult> {
  return request(`/servers/${serverId}/discover?force_refresh=${forceRefresh}`, {
    method: 'POST',
  });
}

export async function refreshServerDiscovery(
  serverId: string,
  forceRefresh: boolean = true
): Promise<MCPDiscoveryResult> {
  return request(`/servers/${serverId}/refresh?force_refresh=${forceRefresh}`, {
    method: 'POST',
  });
}

export async function checkServerHealth(serverId: string): Promise<MCPHealthCheckResult> {
  return request(`/servers/${serverId}/health`);
}

export async function listServerCapabilities(
  serverId: string,
  type?: MCPCapabilityType,
  search?: string,
  includeStale: boolean = true,
  limit: number = 100,
  offset: number = 0
): Promise<{ capabilities: MCPCapability[]; total: number }> {
  const query = new URLSearchParams();
  if (type) query.append('type', type);
  if (search) query.append('search', search);
  if (includeStale !== undefined) query.append('include_stale', includeStale.toString());
  query.append('limit', limit.toString());
  query.append('offset', offset.toString());

  return request(`/servers/${serverId}/capabilities?${query.toString()}`);
}

export async function listServerTools(
  serverId: string,
  search?: string,
  includeStale: boolean = false
): Promise<{ capabilities: MCPCapability[]; total: number }> {
  const query = new URLSearchParams();
  if (search) query.append('search', search);
  if (includeStale) query.append('include_stale', 'true');
  return request(`/servers/${serverId}/tools?${query.toString()}`);
}

export async function listServerResources(
  serverId: string,
  search?: string,
  includeStale: boolean = false
): Promise<{ capabilities: MCPCapability[]; total: number }> {
  const query = new URLSearchParams();
  if (search) query.append('search', search);
  if (includeStale) query.append('include_stale', 'true');
  return request(`/servers/${serverId}/resources?${query.toString()}`);
}

export async function listServerPrompts(
  serverId: string,
  search?: string,
  includeStale: boolean = false
): Promise<{ capabilities: MCPCapability[]; total: number }> {
  const query = new URLSearchParams();
  if (search) query.append('search', search);
  if (includeStale) query.append('include_stale', 'true');
  return request(`/servers/${serverId}/prompts?${query.toString()}`);
}

export async function getCapabilityDetails(capabilityId: string): Promise<MCPCapability> {
  return request(`/capabilities/${capabilityId}`);
}

export async function enableMCPServer(serverId: string): Promise<MCPServer> {
  return request(`/servers/${serverId}/enable`, {
    method: 'POST',
  });
}

export async function disableMCPServer(serverId: string): Promise<MCPServer> {
  return request(`/servers/${serverId}/disable`, {
    method: 'POST',
  });
}
