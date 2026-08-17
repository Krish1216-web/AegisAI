export interface Role {
  id: string;
  name: string;
  description?: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  role: Role;
  avatar_url?: string;
  settings?: Record<string, any>;
}

export interface Token {
  access_token: string;
  token_type: string;
  refresh_token: string;
}

export interface ExecuteRequest {
  message: string;
  workspace_id: string;
  execution_id?: string;
}

export interface ExecuteResponse {
  execution_id: string;
  status: string;
  response?: string;
  confidence: number;
  execution_time: number;
}

export interface ConfirmRequest {
  confirmation_token: string;
}

export interface ExecutionEvent {
  event_type: string;
  agent_type?: string;
  status: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface AgentExecution {
  agent_type: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  retry_count: number;
  quality_score?: number;
  error?: string;
}

export interface StatusResponse {
  execution_id: string;
  status: string;
  current_agent?: string;
  started_at: string;
  completed_at?: string;
  total_execution_time?: number;
  critic_score?: number;
  response_confidence?: number;
  final_response?: string;
  meta_data?: Record<string, any>;
  agent_executions: AgentExecution[];
  events: ExecutionEvent[];
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
