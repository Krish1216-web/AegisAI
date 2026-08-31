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
  last_connected_at?: string;
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
  created_at: string;
  updated_at: string;
}

export interface MCPDiscoveryResult {
  server_id: string;
  server_name: string;
  status: string;
  protocol_version: string;
  total_tools: number;
  total_resources: number;
  total_prompts: number;
  added_capabilities: number;
  updated_capabilities: number;
  pruned_capabilities: number;
  discovery_latency_ms: number;
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
  pruneStale: boolean = true
): Promise<MCPDiscoveryResult> {
  return request(`/servers/${serverId}/discover?prune_stale=${pruneStale}`, {
    method: 'POST',
  });
}

export async function listServerCapabilities(
  serverId: string,
  type?: MCPCapabilityType,
  limit: number = 100,
  offset: number = 0
): Promise<{ capabilities: MCPCapability[]; total: number }> {
  const query = new URLSearchParams();
  if (type) query.append('type', type);
  query.append('limit', limit.toString());
  query.append('offset', offset.toString());

  return request(`/servers/${serverId}/capabilities?${query.toString()}`);
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
