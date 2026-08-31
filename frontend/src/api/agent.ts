import { request, API_BASE_URL } from './client';
import { ExecuteRequest, ExecuteResponse, StatusResponse } from './types';

export async function executeAgentWorkflow(payload: ExecuteRequest): Promise<ExecuteResponse> {
  return request<ExecuteResponse>('/agent/execute', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getExecutionHistory(
  limit: number = 10,
  offset: number = 0,
  status?: string
): Promise<StatusResponse[]> {
  let query = `?limit=${limit}&offset=${offset}`;
  if (status) {
    query += `&status=${status}`;
  }
  return request<StatusResponse[]>(`/agent/executions${query}`, {
    method: 'GET',
  });
}

export async function getExecutionDetails(executionId: string): Promise<StatusResponse> {
  return request<StatusResponse>(`/agent/executions/${executionId}`, {
    method: 'GET',
  });
}

export async function resumeExecution(executionId: string): Promise<ExecuteResponse> {
  return request<ExecuteResponse>(`/agent/executions/${executionId}/resume`, {
    method: 'POST',
  });
}

export async function confirmExecution(
  executionId: string,
  confirmationToken: string
): Promise<ExecuteResponse> {
  return request<ExecuteResponse>(`/agent/executions/${executionId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ confirmation_token: confirmationToken }),
  });
}

export async function cancelExecution(executionId: string): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>(`/agent/executions/${executionId}/cancel`, {
    method: 'POST',
  });
}

export async function streamAgentWorkflow(
  payload: ExecuteRequest,
  onEvent: (event: any) => void,
  onError: (err: any) => void
): Promise<void> {
  const token = localStorage.getItem('aegis_access_token');
  const url = `${API_BASE_URL}/agent/execute/stream`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let msg = `Request failed: ${response.statusText}`;
      try {
        const errorData = await response.json();
        msg = errorData.error?.message || msg;
      } catch {}
      throw new Error(msg);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable.');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          try {
            const rawJson = trimmed.slice(6);
            const parsed = jsonParseSafe(rawJson);
            onEvent(parsed);
          } catch (e) {
            console.error('Failed to parse SSE line:', e);
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
}

function jsonParseSafe(str: string): any {
  try {
    return JSON.parse(str);
  } catch (e) {
    // If it's single quoted json or corrupted, try to replace quotes
    const formatted = str.replace(/'/g, '"');
    return JSON.parse(formatted);
  }
}
