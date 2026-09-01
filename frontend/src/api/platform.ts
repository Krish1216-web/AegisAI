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

export interface PlatformIntelligenceRequest {
  query: string;
  mode?: 'sequential' | 'parallel' | 'adaptive';
  input_data?: Record<string, any>;
  confidence_threshold?: number;
}

export interface PlatformIntelligenceResponse {
  execution_id: string;
  query: string;
  status: string;
  mode: string;
  plan: Record<string, any>;
  decisions: Array<Record<string, any>>;
  evidence_evaluation: Record<string, any>;
  confidence: number;
  confidence_level: string;
  output: Record<string, any>;
  provenance: Array<any>;
  duration_ms: number;
  correlation_id: string;
}

export async function executeIntelligentQuery(payload: PlatformIntelligenceRequest): Promise<PlatformIntelligenceResponse> {
  return request<PlatformIntelligenceResponse>('/platform/intelligence/execute', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

// ==================================================
// Phase 8.8: Observability & Analytics Client
// ==================================================

export interface TimeSeriesPoint {
  timestamp: string;
  total: number;
  completed: number;
  failed: number;
  cancelled: number;
  denied: number;
}

export interface PlatformOverviewMetrics {
  time_window: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  cancelled_executions: number;
  denied_executions: number;
  waiting_executions: number;
  success_rate: number;
  failure_rate: number;
  cancellation_rate: number;
  avg_duration_ms: number;
  median_duration_ms: number;
  p95_duration_ms: number;
  p99_duration_ms: number;
  active_executions: number;
  executions_per_capability: Record<string, number>;
  executions_over_time: TimeSeriesPoint[];
}

export interface CapabilityPerformanceMetric {
  capability_id: string;
  capability_type: string;
  execution_count: number;
  success_count: number;
  failure_count: number;
  denied_count: number;
  cancellation_count: number;
  success_rate: number;
  median_latency_ms: number;
  p95_latency_ms: number;
  error_rate: number;
  health: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'UNKNOWN';
}

export interface CapabilityAnalyticsResponse {
  time_window: string;
  total_capabilities: number;
  items: CapabilityPerformanceMetric[];
}

export interface LifecycleMetrics {
  time_window: string;
  stage_durations_ms: Record<string, number>;
  status_distribution: Record<string, number>;
  status_percentages: Record<string, number>;
}

export interface BottleneckMetric {
  capability_id: string;
  stage: string;
  avg_duration_ms: number;
  p95_duration_ms: number;
  failure_rate: number;
  classification: 'SLOW_EXECUTION' | 'HIGH_FAILURE' | 'HIGH_WAIT' | 'HIGH_VOLUME' | 'NORMAL';
  recommendation: string;
}

export interface BottleneckAnalyticsResponse {
  time_window: string;
  bottlenecks: BottleneckMetric[];
}

export interface IntelligenceAnalytics {
  time_window: string;
  total_executions: number;
  requirement_distribution: Record<string, number>;
  execution_mode_distribution: Record<string, number>;
  decision_distribution: Record<string, number>;
  avg_confidence: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
  insufficient_confidence_count: number;
  adaptive_attempt_distribution: Record<number, number>;
  fallback_count: number;
  retrieve_more_count: number;
  contradiction_count: number;
}

export interface ProvenanceAnalytics {
  time_window: string;
  total_evidence_items: number;
  avg_evidence_per_execution: number;
  source_distribution: Record<string, number>;
  trust_distribution: Record<string, number>;
  citation_frequency: Record<string, number>;
  verified_vs_untrusted_ratio: number;
}

export interface FailureCategoryItem {
  category: string;
  count: number;
  percentage: number;
}

export interface FailureItem {
  error_type: string;
  category: string;
  capability_id: string;
  stage: string;
  normalized_message: string;
  occurrences: number;
  latest_occurrence: string;
}

export interface FailureAnalytics {
  time_window: string;
  total_failures: number;
  failures_by_category: FailureCategoryItem[];
  failures_by_capability: Record<string, number>;
  failures_by_stage: Record<string, number>;
  recent_failures: FailureItem[];
}

export interface PlatformAlert {
  alert_id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  alert_type: string;
  title: string;
  description: string;
  capability_id?: string;
  detected_at: string;
  status: 'ACTIVE' | 'RESOLVED';
}

export interface AlertAnalyticsResponse {
  time_window: string;
  total_alerts: number;
  alerts: PlatformAlert[];
}

export async function getPlatformOverviewMetrics(timeWindow: string = '24h'): Promise<PlatformOverviewMetrics> {
  return request<PlatformOverviewMetrics>(`/platform/analytics/overview?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformCapabilityAnalytics(
  timeWindow: string = '24h',
  capabilityType?: string,
  health?: string
): Promise<CapabilityAnalyticsResponse> {
  const params = new URLSearchParams({ time_window: timeWindow });
  if (capabilityType) params.append('capability_type', capabilityType);
  if (health) params.append('health', health);
  return request<CapabilityAnalyticsResponse>(`/platform/analytics/capabilities?${params.toString()}`);
}

export async function getPlatformLifecycleMetrics(timeWindow: string = '24h'): Promise<LifecycleMetrics> {
  return request<LifecycleMetrics>(`/platform/analytics/lifecycle?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformFailureAnalytics(timeWindow: string = '24h'): Promise<FailureAnalytics> {
  return request<FailureAnalytics>(`/platform/analytics/failures?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformIntelligenceAnalytics(timeWindow: string = '24h'): Promise<IntelligenceAnalytics> {
  return request<IntelligenceAnalytics>(`/platform/analytics/intelligence?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformProvenanceAnalytics(timeWindow: string = '24h'): Promise<ProvenanceAnalytics> {
  return request<ProvenanceAnalytics>(`/platform/analytics/provenance?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformBottleneckAnalytics(timeWindow: string = '24h'): Promise<BottleneckAnalyticsResponse> {
  return request<BottleneckAnalyticsResponse>(`/platform/analytics/bottlenecks?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformAlerts(timeWindow: string = '24h'): Promise<AlertAnalyticsResponse> {
  return request<AlertAnalyticsResponse>(`/platform/analytics/alerts?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getPlatformExecutionTimeline(executionId: string): Promise<any> {
  return request<any>(`/platform/analytics/executions/${encodeURIComponent(executionId)}/timeline`);
}

