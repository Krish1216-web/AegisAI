import { request } from './client';

export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived';
export type WorkflowExecutionStatus = 'pending' | 'running' | 'waiting' | 'completed' | 'failed' | 'cancelled';
export type WorkflowNodeStatus = 'pending' | 'running' | 'waiting' | 'completed' | 'failed' | 'skipped' | 'cancelled';

export type WorkflowNodeType =
  | 'start'
  | 'end'
  | 'agent'
  | 'rag'
  | 'graph'
  | 'memory'
  | 'mcp_tool'
  | 'mcp_resource'
  | 'mcp_prompt'
  | 'local_tool'
  | 'condition'
  | 'human_approval'
  | 'transform';

export interface WorkflowNode {
  id: string;
  workflow_id: string;
  node_key: string;
  node_type: WorkflowNodeType;
  name: string;
  config: Record<string, any>;
  position: { x: number; y: number };
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowEdge {
  id: string;
  workflow_id: string;
  source_node_id: string;
  target_node_id: string;
  condition?: Record<string, any> | null;
  priority: number;
  created_at: string;
}

export interface WorkflowVariable {
  id: string;
  workflow_id: string;
  name: string;
  value?: string | null;
  value_type: string;
  is_secret: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowSummary {
  id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: WorkflowStatus;
  version: number;
  is_active: boolean;
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends WorkflowSummary {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: WorkflowVariable[];
}

export interface WorkflowValidationItem {
  code: string;
  message: string;
  node_key?: string | null;
  edge_id?: string | null;
}

export interface WorkflowValidationResult {
  valid: boolean;
  errors: WorkflowValidationItem[];
  warnings: WorkflowValidationItem[];
}

export interface WorkflowExecutionSummary {
  id: string;
  workflow_id: string;
  workflow_version: number;
  user_id: string;
  workspace_id: string;
  status: WorkflowExecutionStatus;
  input_data: Record<string, any>;
  output_data?: Record<string, any> | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface WorkflowExecutionNodeRecord {
  id: string;
  execution_id: string;
  node_id?: string | null;
  node_key: string;
  status: WorkflowNodeStatus;
  input_data?: Record<string, any> | null;
  output_data?: Record<string, any> | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface WorkflowExecutionDetail extends WorkflowExecutionSummary {
  execution_nodes: WorkflowExecutionNodeRecord[];
}

export const getWorkflows = async (params?: { limit?: number; offset?: number; status?: string }): Promise<{ workflows: WorkflowSummary[]; total: number }> => {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  if (params?.status) query.set('status', params.status);
  const qStr = query.toString();
  return request<{ workflows: WorkflowSummary[]; total: number }>(`/workflows${qStr ? `?${qStr}` : ''}`, { method: 'GET' });
};

export const getWorkflow = async (id: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}`, { method: 'GET' });
};

export const createWorkflow = async (payload: {
  name: string;
  description?: string;
  nodes?: any[];
  edges?: any[];
  variables?: any[];
}): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>('/workflows', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
};

export const updateWorkflow = async (
  id: string,
  payload: {
    name?: string;
    description?: string;
    status?: WorkflowStatus;
    is_active?: boolean;
    nodes?: any[];
    edges?: any[];
    variables?: any[];
  }
): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  });
};

export const getWorkflowDefinition = async (id: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/definition`, { method: 'GET' });
};

export const updateWorkflowDefinition = async (
  id: string,
  payload: {
    expected_version: number;
    name?: string;
    description?: string;
    nodes: any[];
    edges: any[];
    variables?: any[];
  }
): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/definition`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  });
};

export const cloneWorkflow = async (id: string, name?: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/clone`, {
    method: 'POST',
    body: JSON.stringify({ name })
  });
};

export const deleteWorkflow = async (id: string): Promise<void> => {
  return request<void>(`/workflows/${id}`, { method: 'DELETE' });
};

export const validateWorkflow = async (id: string): Promise<WorkflowValidationResult> => {
  return request<WorkflowValidationResult>(`/workflows/${id}/validate`, { method: 'POST' });
};

export const activateWorkflow = async (id: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/activate`, { method: 'POST' });
};

export const pauseWorkflow = async (id: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/pause`, { method: 'POST' });
};

export const archiveWorkflow = async (id: string): Promise<WorkflowDetail> => {
  return request<WorkflowDetail>(`/workflows/${id}/archive`, { method: 'POST' });
};

export const executeWorkflow = async (id: string, inputData: Record<string, any> = {}): Promise<WorkflowExecutionDetail> => {
  return request<WorkflowExecutionDetail>(`/workflows/${id}/execute`, {
    method: 'POST',
    body: JSON.stringify({ input_data: inputData })
  });
};

export const getWorkflowExecutions = async (id: string, params?: { limit?: number; offset?: number }): Promise<WorkflowExecutionSummary[]> => {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  const qStr = query.toString();
  return request<WorkflowExecutionSummary[]>(`/workflows/${id}/executions${qStr ? `?${qStr}` : ''}`, { method: 'GET' });
};

export const getWorkflowExecution = async (executionId: string): Promise<WorkflowExecutionDetail> => {
  return request<WorkflowExecutionDetail>(`/workflows/executions/${executionId}`, { method: 'GET' });
};

export const cancelWorkflowExecution = async (executionId: string): Promise<WorkflowExecutionSummary> => {
  return request<WorkflowExecutionSummary>(`/workflows/executions/${executionId}/cancel`, { method: 'POST' });
};

export const approveWorkflowExecution = async (
  executionId: string,
  approved: boolean = true,
  comments?: string
): Promise<WorkflowExecutionSummary> => {
  return request<WorkflowExecutionSummary>(`/workflows/executions/${executionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved, comments })
  });
};

export interface WorkflowApproval {
  id: string;
  execution_id: string;
  workflow_id: string;
  workflow_node_id?: string | null;
  workspace_id: string;
  node_key: string;
  requested_by: string;
  assigned_roles: string[];
  assigned_users: string[];
  status: string;
  policy: string;
  required_count: number;
  requester_can_approve: boolean;
  title: string;
  message?: string | null;
  timeout_seconds: number;
  expires_at?: string | null;
  decided_by?: string | null;
  decided_at?: string | null;
  decision?: string | null;
  reason?: string | null;
  decision_history: any[];
  created_at: string;
  updated_at: string;
}

export const getWorkflowApprovals = async (params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ approvals: WorkflowApproval[]; total: number }> => {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  const qStr = query.toString();
  return request<{ approvals: WorkflowApproval[]; total: number }>(`/workflows/approvals${qStr ? `?${qStr}` : ''}`, {
    method: 'GET'
  });
};

export const getWorkflowApproval = async (approvalId: string): Promise<WorkflowApproval> => {
  return request<WorkflowApproval>(`/workflows/approvals/${approvalId}`, { method: 'GET' });
};

export const approveWorkflowApproval = async (
  approvalId: string,
  reason?: string
): Promise<WorkflowApproval> => {
  return request<WorkflowApproval>(`/workflows/approvals/${approvalId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ decision: 'approved', reason })
  });
};

export const rejectWorkflowApproval = async (
  approvalId: string,
  reason?: string
): Promise<WorkflowApproval> => {
  return request<WorkflowApproval>(`/workflows/approvals/${approvalId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ decision: 'rejected', reason })
  });
};
