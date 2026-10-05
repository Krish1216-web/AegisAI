import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import UserDashboard from '../pages/user/UserDashboard';
import AdminDashboard from '../pages/admin/AdminDashboard';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthContext } from '../context/AuthContext';

// Mock matchMedia
window.matchMedia = window.matchMedia || function () {
  return {
    matches: false,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
};

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock API calls
vi.mock('../api/platform', () => ({
  getPlatformStatus: vi.fn().mockResolvedValue({
    version: '1.0.0',
    phase: '12.3',
    workspace_id: 'ws-prod-01',
    active_capabilities: 7,
    system_health: 'ONLINE',
    feature_flags: {},
    registered_subsystems: ['agent', 'rag', 'memory', 'mcp', 'workflow']
  }),
  getPlatformOverviewMetrics: vi.fn().mockResolvedValue({
    total_executions: 120,
    successful_executions: 118,
    failed_executions: 2,
    success_rate: 98.3,
    avg_duration_ms: 240,
    active_executions: 1
  }),
  getPlatformCapabilities: vi.fn().mockResolvedValue({
    total: 7,
    items: [
      { capability_id: 'agent-orch', name: 'Agent Collective', enabled: true },
      { capability_id: 'rag-engine', name: 'Enterprise RAG', enabled: true }
    ]
  }),
  getPlatformAlerts: vi.fn().mockResolvedValue({
    total_alerts: 0,
    alerts: []
  }),
  executeIntelligentQuery: vi.fn().mockResolvedValue({
    execution_id: 'exec-test-889',
    query: 'Analyze quarterly trends',
    status: 'completed',
    mode: 'adaptive',
    output: { summary: 'Quarterly telemetry processed across 14 data points.' },
    confidence: 0.96,
    confidence_level: 'HIGH',
    duration_ms: 185,
    provenance: [{ id: 'p1', source_type: 'document' }]
  })
}));

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn().mockResolvedValue([
    { id: 'doc-1', filename: 'architecture.pdf', status: 'INDEXED' },
    { id: 'doc-2', filename: 'security.pdf', status: 'INDEXED' }
  ])
}));

vi.mock('../api/workflows', () => ({
  getWorkflows: vi.fn().mockResolvedValue({
    workflows: [{ id: 'wf-1', name: 'PR Auto Review' }],
    total: 3
  })
}));

vi.mock('../api/mcp', () => ({
  listMCPServers: vi.fn().mockResolvedValue({
    servers: [{ id: 'mcp-1', name: 'Local File Server' }],
    total: 4
  })
}));

vi.mock('../api/admin', () => ({
  getAdminOverview: vi.fn().mockResolvedValue({
    total_users: 48,
    active_users: 32,
    total_workspaces: 6,
    total_executions: 1420,
    success_rate: 99.1,
    avg_latency_ms: 14,
    system_status: 'ONLINE',
    alerts_count: 0
  }),
  getAdminSystemHealth: vi.fn().mockResolvedValue({
    environment: 'Production',
    subsystems: [
      { name: 'PostgreSQL Primary', status: 'ONLINE', latency_ms: 1.2 },
      { name: 'Redis Cache', status: 'ONLINE', latency_ms: 0.8 },
      { name: 'Qdrant Vector Engine', status: 'ONLINE', latency_ms: 2.1 }
    ]
  }),
  getAdminActivityFeed: vi.fn().mockResolvedValue({
    events: [
      { summary: 'Agent DAG plan executed successfully', source_component: 'ORCH', timestamp: new Date().toISOString() },
      { summary: 'Document chunk vector embeddings sealed', source_component: 'RAG', timestamp: new Date().toISOString() }
    ]
  })
}));

function renderUserDashboard(authOverrides = {}) {
  const defaultAuth = {
    isAuthenticated: true,
    token: 'test-token',
    user: { username: 'testuser' },
    role: 'member',
    workspaceId: 'ws-prod-01',
    login: vi.fn(),
    logout: vi.fn(),
    ...authOverrides
  };

  return render(
    <AuthContext.Provider value={defaultAuth}>
      <ThemeProvider>
        <HashRouter>
          <UserDashboard />
        </HashRouter>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

function renderAdminDashboard() {
  const defaultAuth = {
    isAuthenticated: true,
    token: 'admin-token',
    user: { username: 'adminuser' },
    role: 'admin',
    workspaceId: 'ws-admin-01',
    login: vi.fn(),
    logout: vi.fn()
  };

  return render(
    <AuthContext.Provider value={defaultAuth}>
      <ThemeProvider>
        <HashRouter>
          <AdminDashboard />
        </HashRouter>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

describe('Phase 12.3 — AI OS Workspace & Dashboard Experience', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. Workspace Header & Identity
  // ============================================================================
  it('renders Mission Control header, workspace ID, and role badge', async () => {
    renderUserDashboard({ role: 'member', workspaceId: 'ws-prod-alpha' });

    expect(screen.getByText(/AegisAI OS — Mission Control/i)).toBeInTheDocument();
    expect(screen.getByText('ws-prod-alpha')).toBeInTheDocument();
    expect(screen.getByText('MEMBER')).toBeInTheDocument();
  });

  it('displays truthful system status badge', async () => {
    renderUserDashboard();

    await waitFor(() => {
      expect(screen.getAllByText('ONLINE').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders read-only banner when role is viewer', () => {
    renderUserDashboard({ role: 'viewer' });

    expect(screen.getByText(/read-only inspection mode/i)).toBeInTheDocument();
  });

  // ============================================================================
  // 2. Primary AI Workspace Console ("Ask AegisAI")
  // ============================================================================
  it('renders Primary AI Workspace Console and mode selector', () => {
    renderUserDashboard();

    expect(screen.getByText('Primary AI Workspace Console')).toBeInTheDocument();
    expect(screen.getByText('adaptive')).toBeInTheDocument();
    expect(screen.getByText('parallel')).toBeInTheDocument();
    expect(screen.getByText('sequential')).toBeInTheDocument();
  });

  it('allows toggling execution mode pills', () => {
    renderUserDashboard();

    const parallelBtn = screen.getByRole('button', { name: 'parallel' });
    fireEvent.click(parallelBtn);
    expect(parallelBtn).toHaveClass('bg-cyan-500/20');
  });

  it('disables submit button when prompt input is empty', () => {
    renderUserDashboard();

    const submitBtn = screen.getByRole('button', { name: /Execute Query/i });
    expect(submitBtn).toBeDisabled();
  });

  it('enables submit button when prompt is typed', () => {
    renderUserDashboard();

    const textarea = screen.getByPlaceholderText(/Describe your operational goal/i);
    fireEvent.change(textarea, { target: { value: 'Synthesize quarterly memory vectors' } });

    const submitBtn = screen.getByRole('button', { name: /Execute Query/i });
    expect(submitBtn).not.toBeDisabled();
  });

  it('submits query when Enter key is pressed without Shift', async () => {
    renderUserDashboard();

    const textarea = screen.getByPlaceholderText(/Describe your operational goal/i);
    fireEvent.change(textarea, { target: { value: 'Run task decomposition' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText(/Execution Status/i)).toBeInTheDocument();
      expect(screen.getByText(/Evidence Items:/i)).toBeInTheDocument();
    });
  });

  it('does not submit query on Shift+Enter (allows multiline)', () => {
    renderUserDashboard();

    const textarea = screen.getByPlaceholderText(/Describe your operational goal/i);
    fireEvent.change(textarea, { target: { value: 'First line of prompt' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true });

    // Status card should not appear
    expect(screen.queryByText(/Execution Status/i)).not.toBeInTheDocument();
  });

  it('disables prompt submission when user has viewer role', () => {
    renderUserDashboard({ role: 'viewer' });

    const textarea = screen.getByPlaceholderText(/Viewer role — prompt submission disabled/i);
    expect(textarea).toBeDisabled();
  });

  // ============================================================================
  // 3. Operational Quick Actions
  // ============================================================================
  it('renders all 6 operational quick actions', () => {
    renderUserDashboard();

    expect(screen.getAllByText('Ask AegisAI').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Build Workflow')).toBeInTheDocument();
    expect(screen.getByText('Upload Documents')).toBeInTheDocument();
    expect(screen.getByText('Explore Graph')).toBeInTheDocument();
    expect(screen.getByText('Connect MCP')).toBeInTheDocument();
    expect(screen.getByText('Memory Vault')).toBeInTheDocument();
  });

  it('navigates to target route when quick action is clicked', () => {
    renderUserDashboard();

    const buildAction = screen.getByText('Build Workflow');
    fireEvent.click(buildAction);
    expect(mockNavigate).toHaveBeenCalledWith('/user/workflows');
  });

  it('disables write quick actions for viewer role', () => {
    renderUserDashboard({ role: 'viewer' });

    const workflowActionBtn = screen.getByText('Build Workflow').closest('button');
    expect(workflowActionBtn).toBeDisabled();
  });

  // ============================================================================
  // 4. Attention Center
  // ============================================================================
  it('renders positive nominal state when no workspace alerts exist', async () => {
    renderUserDashboard();

    await waitFor(() => {
      expect(screen.getByText(/Nothing requires your attention/i)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // 5. Capability Map Overview
  // ============================================================================
  it('renders all 7 platform capability cards', () => {
    renderUserDashboard();

    expect(screen.getByText('Agent Collective')).toBeInTheDocument();
    expect(screen.getByText('Knowledge & RAG')).toBeInTheDocument();
    expect(screen.getByText('Cognitive Memory')).toBeInTheDocument();
    expect(screen.getByText('MCP Tool Ecosystem')).toBeInTheDocument();
    expect(screen.getByText('Workflow Engine')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    expect(screen.getByText('Execution Engine')).toBeInTheDocument();
  });

  it('navigates when capability card is clicked', () => {
    renderUserDashboard();

    const memoryCard = screen.getByText('Cognitive Memory');
    fireEvent.click(memoryCard);
    expect(mockNavigate).toHaveBeenCalledWith('/user/memory');
  });

  // ============================================================================
  // 6. Snapshots
  // ============================================================================
  it('renders Knowledge & Memory snapshot', async () => {
    renderUserDashboard();

    expect(screen.getByText('Knowledge & Cognitive Memory Snapshot')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('DOCUMENTS INDEXED')).toBeInTheDocument();
      expect(screen.getByText('RAG Ready')).toBeInTheDocument();
    });
  });

  it('renders 6 architectural system agents in workforce snapshot', () => {
    renderUserDashboard();

    expect(screen.getByText('Active System Agent Workforce')).toBeInTheDocument();
    expect(screen.getByText('Orchestrator Agent')).toBeInTheDocument();
    expect(screen.getByText('Planner Agent')).toBeInTheDocument();
    expect(screen.getByText('Research Agent')).toBeInTheDocument();
    expect(screen.getByText('Tool Executor')).toBeInTheDocument();
    expect(screen.getByText('Critic & Consensus')).toBeInTheDocument();
    expect(screen.getByText('Response Generator')).toBeInTheDocument();
  });

  it('renders MCP Ecosystem snapshot with daemon count', async () => {
    renderUserDashboard();

    expect(screen.getByText('MCP Tool Ecosystem Snapshot')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Registered MCP Daemons')).toBeInTheDocument();
    });
  });

  it('renders Workflow Automation snapshot with active workflows count', async () => {
    renderUserDashboard();

    expect(screen.getByText('Workflow Automation Snapshot')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Active Workflows')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // 7. Recent Operational Activity Feed
  // ============================================================================
  it('renders recent operational activity feed with events', async () => {
    renderUserDashboard();

    await waitFor(() => {
      expect(screen.getByText('Recent Operational Activity Feed')).toBeInTheDocument();
      expect(screen.getByText('Agent DAG plan executed successfully')).toBeInTheDocument();
    });
  });

  it('triggers manual refresh on Sync button click', async () => {
    renderUserDashboard();

    const syncBtn = screen.getByRole('button', { name: /Sync/i });
    fireEvent.click(syncBtn);
    expect(syncBtn).toBeInTheDocument();
  });

  // ============================================================================
  // 8. Admin Dashboard Tests
  // ============================================================================
  it('renders Admin Dashboard header and portal badge', async () => {
    renderAdminDashboard();

    expect(screen.getByText('Enterprise Operations Center')).toBeInTheDocument();
    expect(screen.getByText('ADMIN PORTAL')).toBeInTheDocument();
  });

  it('renders Admin KPI metric cards', async () => {
    renderAdminDashboard();

    await waitFor(() => {
      expect(screen.getByText('Active Users')).toBeInTheDocument();
      expect(screen.getByText('Executions Volume')).toBeInTheDocument();
      expect(screen.getByText('Avg Latency')).toBeInTheDocument();
    });
  });

  it('renders Admin subsystem health diagnostics grid', async () => {
    renderAdminDashboard();

    await waitFor(() => {
      expect(screen.getByText('Subsystem Health & Dependency Diagnostics')).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL Primary')).toBeInTheDocument();
      expect(screen.getByText('Redis Cache')).toBeInTheDocument();
      expect(screen.getByText('Qdrant Vector Engine')).toBeInTheDocument();
    });
  });

  it('allows switching time window in Admin Dashboard', async () => {
    renderAdminDashboard();

    const btn7d = screen.getByRole('button', { name: '7d' });
    fireEvent.click(btn7d);
    expect(btn7d).toHaveClass('bg-purple-500/20');
  });
});
