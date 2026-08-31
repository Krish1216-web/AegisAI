export type MCPTransport = 'sse' | 'streamable_http' | 'stdio';
export type MCPServerStatus = 'active' | 'inactive' | 'error' | 'disabled';
export type MCPCapabilityType = 'tool' | 'resource' | 'prompt';
export type MCPAuthenticationType = 'none' | 'api_key' | 'bearer' | 'oauth';
export type ToolRiskLevel = 'safe' | 'restricted' | 'invalid';
export type ToolPolicyDecision = 'allow' | 'require_confirmation' | 'deny';

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

export interface MCPTool {
  id: string;
  server_id: string;
  server_name: string;
  server_transport: string;
  server_status: string;
  server_enabled: boolean;
  name: string;
  description?: string;
  input_schema?: Record<string, any>;
  metadata?: Record<string, any>;
  enabled: boolean;
  is_stale: boolean;
  stale_at?: string;
  definition_hash?: string;
  version: number;
  risk_level: ToolRiskLevel;
  policy_decision: ToolPolicyDecision;
  risk_reasons: string[];
  available_for_execution: boolean;
  first_discovered_at?: string;
  last_discovered_at?: string;
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

// Servers
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

// Capabilities
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

export async function getCapabilityDetails(capabilityId: string): Promise<MCPCapability> {
  return request(`/capabilities/${capabilityId}`);
}

// Tool Catalog (Phase 6.3)
export async function listWorkspaceTools(params?: {
  server_id?: string;
  enabled_only?: boolean;
  include_stale?: boolean;
  risk_level?: ToolRiskLevel;
  transport?: MCPTransport;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ tools: MCPTool[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.server_id) query.append('server_id', params.server_id);
  if (params?.enabled_only) query.append('enabled_only', 'true');
  if (params?.include_stale !== undefined) query.append('include_stale', params.include_stale.toString());
  if (params?.risk_level) query.append('risk_level', params.risk_level);
  if (params?.transport) query.append('transport', params.transport);
  if (params?.search) query.append('search', params.search);
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset) query.append('offset', params.offset.toString());

  return request(`/tools?${query.toString()}`);
}

export async function searchWorkspaceTools(payload: {
  query: string;
  server_id?: string;
  risk_level?: ToolRiskLevel;
  enabled_only?: boolean;
  include_stale?: boolean;
  limit?: number;
}): Promise<{ results: MCPTool[]; total: number; query: string }> {
  return request('/tools/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getToolDetails(toolId: string): Promise<MCPTool> {
  return request(`/tools/${toolId}`);
}

export async function enableMCPTool(toolId: string): Promise<MCPTool> {
  return request(`/tools/${toolId}/enable`, {
    method: 'POST',
  });
}

export async function disableMCPTool(toolId: string): Promise<MCPTool> {
  return request(`/tools/${toolId}/disable`, {
    method: 'POST',
  });
}

// Tool Execution (Phase 6.4)
export interface MCPToolExecutionResult {
  execution_id: string;
  tool_id: string;
  tool_name: string;
  status: string;
  result: Record<string, any>;
  text_content?: string;
  duration_ms: number;
  retry_count: number;
  truncated: boolean;
  error?: string;
}

export interface MCPToolConfirmationResult {
  token: string;
  tool_id: string;
  expires_in_seconds: number;
  risk_level: string;
  risk_reasons: string[];
}

export async function generateToolConfirmationToken(
  toolId: string,
  argumentsPayload: Record<string, any>
): Promise<MCPToolConfirmationResult> {
  return request(`/tools/${toolId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ arguments: argumentsPayload }),
  });
}

export async function executeMCPTool(
  toolId: string,
  payload: {
    arguments: Record<string, any>;
    confirmation_token?: string;
    timeout?: number;
  }
): Promise<MCPToolExecutionResult> {
  return request(`/tools/${toolId}/execute`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ==========================================
// Phase 6.5 Resources API
// ==========================================

export interface MCPResource {
  id: string;
  server_id: string;
  server_name: string;
  server_transport: string;
  server_status: string;
  server_enabled: boolean;
  name: string;
  uri: string;
  mime_type?: string;
  description?: string;
  metadata?: Record<string, any>;
  enabled: boolean;
  is_stale: boolean;
  stale_at?: string;
  definition_hash?: string;
  version: number;
  first_discovered_at?: string;
  last_discovered_at?: string;
  created_at: string;
  updated_at: string;
}

export interface MCPResourceReadResult {
  uri: string;
  mime_type?: string;
  text?: string;
  size: number;
  truncated: boolean;
  metadata: Record<string, any>;
}

export async function listMCPResources(params?: {
  server_id?: string;
  search?: string;
  enabled_only?: boolean;
  include_stale?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ resources: MCPResource[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.server_id) query.append('server_id', params.server_id);
  if (params?.search) query.append('search', params.search);
  if (params?.enabled_only !== undefined) query.append('enabled_only', String(params.enabled_only));
  if (params?.include_stale !== undefined) query.append('include_stale', String(params.include_stale));
  if (params?.limit) query.append('limit', String(params.limit));
  if (params?.offset) query.append('offset', String(params.offset));

  return request(`/resources?${query.toString()}`);
}

export async function searchMCPResources(payload: {
  query: string;
  server_id?: string;
  enabled_only?: boolean;
  include_stale?: boolean;
  limit?: number;
}): Promise<{ results: MCPResource[]; total: number; query: string }> {
  return request('/resources/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function readMCPResource(resourceId: string, timeout?: number): Promise<MCPResourceReadResult> {
  const query = timeout ? `?timeout=${timeout}` : '';
  return request(`/resources/${resourceId}/read${query}`, {
    method: 'POST',
  });
}

export async function enableMCPResource(resourceId: string): Promise<MCPResource> {
  return request(`/resources/${resourceId}/enable`, {
    method: 'POST',
  });
}

export async function disableMCPResource(resourceId: string): Promise<MCPResource> {
  return request(`/resources/${resourceId}/disable`, {
    method: 'POST',
  });
}

// ==========================================
// Phase 6.5 Prompts API
// ==========================================

export interface MCPPrompt {
  id: string;
  server_id: string;
  server_name: string;
  server_transport: string;
  server_status: string;
  server_enabled: boolean;
  name: string;
  description?: string;
  arguments: Array<{
    name: string;
    description?: string;
    required?: boolean;
  }>;
  metadata?: Record<string, any>;
  enabled: boolean;
  is_stale: boolean;
  stale_at?: string;
  definition_hash?: string;
  version: number;
  first_discovered_at?: string;
  last_discovered_at?: string;
  created_at: string;
  updated_at: string;
}

export interface MCPPromptRenderResult {
  prompt_id: string;
  name: string;
  description?: string;
  messages: Array<{
    role: string;
    content: string;
    untrusted: boolean;
  }>;
  untrusted: boolean;
}

export async function listMCPPrompts(params?: {
  server_id?: string;
  search?: string;
  enabled_only?: boolean;
  include_stale?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ prompts: MCPPrompt[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.server_id) query.append('server_id', params.server_id);
  if (params?.search) query.append('search', params.search);
  if (params?.enabled_only !== undefined) query.append('enabled_only', String(params.enabled_only));
  if (params?.include_stale !== undefined) query.append('include_stale', String(params.include_stale));
  if (params?.limit) query.append('limit', String(params.limit));
  if (params?.offset) query.append('offset', String(params.offset));

  return request(`/prompts?${query.toString()}`);
}

export async function searchMCPPrompts(payload: {
  query: string;
  server_id?: string;
  enabled_only?: boolean;
  include_stale?: boolean;
  limit?: number;
}): Promise<{ results: MCPPrompt[]; total: number; query: string }> {
  return request('/prompts/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function renderMCPPrompt(
  promptId: string,
  argumentsPayload: Record<string, any>,
  timeout?: number
): Promise<MCPPromptRenderResult> {
  const query = timeout ? `?timeout=${timeout}` : '';
  return request(`/prompts/${promptId}/render${query}`, {
    method: 'POST',
    body: JSON.stringify({ arguments: argumentsPayload }),
  });
}

export async function enableMCPPrompt(promptId: string): Promise<MCPPrompt> {
  return request(`/prompts/${promptId}/enable`, {
    method: 'POST',
  });
}

export async function disableMCPPrompt(promptId: string): Promise<MCPPrompt> {
  return request(`/prompts/${promptId}/disable`, {
    method: 'POST',
  });
}


