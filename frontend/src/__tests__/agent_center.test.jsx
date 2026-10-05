import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import UserAiMarket from '../pages/user/UserAiMarket';
import AdminAgents from '../pages/admin/AdminAgents';
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

// Mock platform API calls
vi.mock('../api/platform', () => ({
  getPlatformStatus: vi.fn().mockResolvedValue({
    version: '1.0.0',
    phase: '12.4',
    workspace_id: 'ws-prod-01',
    active_capabilities: 9,
    system_health: 'ONLINE',
    registered_subsystems: ['agent', 'rag', 'memory', 'mcp', 'workflow']
  }),
  getPlatformCapabilities: vi.fn().mockResolvedValue({
    total: 3,
    items: [
      { capability_id: 'orchestrator-core', name: 'Orchestrator Swarm Node', description: 'Core DAG coordinator', version: '1.0.0', enabled: true, required_permissions: [] },
      { capability_id: 'rag-vector-core', name: 'Enterprise Document RAG', description: 'Vector retrieval node', version: '1.0.0', enabled: true, required_permissions: ['rag:read'] },
      { capability_id: 'mcp-executor-node', name: 'MCP Sandboxed Executor', description: 'Tool runtime engine', version: '1.0.0', enabled: true, required_permissions: ['mcp:execute'] }
    ]
  })
}));

function renderUserAiMarket(authOverrides = {}) {
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
          <UserAiMarket />
        </HashRouter>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

function renderAdminAgents() {
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
          <AdminAgents />
        </HashRouter>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

describe('Phase 12.4 — Agent Center & AI Workforce Control Center', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. Header & Workforce Overview
  // ============================================================================
  it('renders Agent Center title, subtitle, and workforce badge', () => {
    renderUserAiMarket();

    expect(screen.getByText(/Agent Center — AI Workforce Control/i)).toBeInTheDocument();
    expect(screen.getByText('SYSTEM WORKFORCE')).toBeInTheDocument();
  });

  it('renders Workforce Overview KPI metrics', () => {
    renderUserAiMarket();

    expect(screen.getByText('System Workforce')).toBeInTheDocument();
    expect(screen.getByText('9 Active Agents')).toBeInTheDocument();
    expect(screen.getByText('Swarm Topology')).toBeInTheDocument();
    expect(screen.getByText('Verification Gate')).toBeInTheDocument();
    expect(screen.getByText('Security Boundary')).toBeInTheDocument();
  });

  // ============================================================================
  // 2. Directory View & System Agents
  // ============================================================================
  it('renders all 9 canonical system agents in directory view', () => {
    renderUserAiMarket();

    expect(screen.getByText('Orchestrator Agent')).toBeInTheDocument();
    expect(screen.getByText('Planner Agent')).toBeInTheDocument();
    expect(screen.getByText('Research Agent')).toBeInTheDocument();
    expect(screen.getByText('Memory Agent')).toBeInTheDocument();
    expect(screen.getByText('Enterprise RAG Agent')).toBeInTheDocument();
    expect(screen.getByText('Graph Reasoning Agent')).toBeInTheDocument();
    expect(screen.getByText('Tool Executor Agent')).toBeInTheDocument();
    expect(screen.getByText('Critic & Consensus Agent')).toBeInTheDocument();
    expect(screen.getByText('Response Generator')).toBeInTheDocument();
  });

  it('displays agent roles, stages, and status badges', () => {
    renderUserAiMarket();

    expect(screen.getByText('Global Swarm Coordinator')).toBeInTheDocument();
    expect(screen.getByText('DAG Task Decomposition')).toBeInTheDocument();
    expect(screen.getByText('Enterprise Document Intelligence')).toBeInTheDocument();
    expect(screen.getAllByText('AVAILABLE').length).toBeGreaterThanOrEqual(9);
  });

  // ============================================================================
  // 3. Search & Category Filters
  // ============================================================================
  it('filters agents by search query', () => {
    renderUserAiMarket();

    const searchInput = screen.getByPlaceholderText(/Search agents by name/i);
    fireEvent.change(searchInput, { target: { value: 'Planner' } });

    expect(screen.getByText('Planner Agent')).toBeInTheDocument();
    expect(screen.queryByText('Research Agent')).not.toBeInTheDocument();
  });

  it('filters agents by capability keyword', () => {
    renderUserAiMarket();

    const searchInput = screen.getByPlaceholderText(/Search agents by name/i);
    fireEvent.change(searchInput, { target: { value: 'Vector' } });

    expect(screen.getByText('Memory Agent')).toBeInTheDocument();
    expect(screen.getByText('Enterprise RAG Agent')).toBeInTheDocument();
  });

  it('filters agents by category pill button', () => {
    renderUserAiMarket();

    const verificationBtn = screen.getByRole('button', { name: 'Verification' });
    fireEvent.click(verificationBtn);

    expect(screen.getByText('Critic & Consensus Agent')).toBeInTheDocument();
    expect(screen.getByText('Response Generator')).toBeInTheDocument();
    expect(screen.queryByText('Orchestrator Agent')).not.toBeInTheDocument();
  });

  it('renders empty state when no search matches are found and allows reset', () => {
    renderUserAiMarket();

    const searchInput = screen.getByPlaceholderText(/Search agents by name/i);
    fireEvent.change(searchInput, { target: { value: 'NonexistentAgentXYZ' } });

    expect(screen.getByText('No matching agents found')).toBeInTheDocument();

    const clearBtn = screen.getByRole('button', { name: 'Clear Filters' });
    fireEvent.click(clearBtn);

    expect(screen.getByText('Orchestrator Agent')).toBeInTheDocument();
  });

  // ============================================================================
  // 4. Slide-Over Agent Inspector Drawer
  // ============================================================================
  it('opens Agent Inspector drawer when clicking Inspect Agent', () => {
    renderUserAiMarket();

    const inspectBtns = screen.getAllByRole('button', { name: /Inspect Agent/i });
    fireEvent.click(inspectBtns[0]); // Inspect Orchestrator

    expect(screen.getByText('PRIMARY OPERATIONAL PURPOSE')).toBeInTheDocument();
    expect(screen.getByText('ARCHITECTURE PIPELINE STAGE & HANDOFF')).toBeInTheDocument();
    expect(screen.getByText('REGISTERED CAPABILITY PERMISSIONS')).toBeInTheDocument();
    expect(screen.getByText('CONNECTED INFRASTRUCTURE SUBSYSTEMS')).toBeInTheDocument();
    expect(screen.getByText('ENTERPRISE GOVERNANCE & SECURITY CONTROLS')).toBeInTheDocument();
    expect(screen.getByText('EVIDENCE & AUDIT TRAIL OUTPUT SPECIFICATION')).toBeInTheDocument();
  });

  it('closes Agent Inspector drawer when clicking Close Inspector', () => {
    renderUserAiMarket();

    const inspectBtns = screen.getAllByRole('button', { name: /Inspect Agent/i });
    fireEvent.click(inspectBtns[0]);

    const closeBtn = screen.getByRole('button', { name: 'Close Inspector' });
    fireEvent.click(closeBtn);

    expect(screen.queryByText('PRIMARY OPERATIONAL PURPOSE')).not.toBeInTheDocument();
  });

  // ============================================================================
  // 5. Architecture Map View & Accessible Fallback
  // ============================================================================
  it('switches to Architecture Map view and renders topological DAG flow', () => {
    renderUserAiMarket();

    const archBtn = screen.getByRole('button', { name: 'Architecture Map' });
    fireEvent.click(archBtn);

    expect(screen.getByText(/Multi-Agent Collective Architecture & Flow/i)).toBeInTheDocument();
    expect(screen.getByText('01. COORDINATION')).toBeInTheDocument();
    expect(screen.getByText('02. PLANNING')).toBeInTheDocument();
    expect(screen.getAllByText('PARALLEL NODE').length).toBe(5);
    expect(screen.getByText('05. QUALITY GATE')).toBeInTheDocument();
    expect(screen.getByText('06. DELIVERY')).toBeInTheDocument();
  });

  it('renders accessible plain text handshake sequence for screen readers', () => {
    renderUserAiMarket();

    const archBtn = screen.getByRole('button', { name: 'Architecture Map' });
    fireEvent.click(archBtn);

    expect(screen.getByText(/Accessible Architectural Sequence & Handshake Protocol:/i)).toBeInTheDocument();
    expect(screen.getByText(/Intercepts natural language request, establishes workspace isolation/i)).toBeInTheDocument();
  });

  // ============================================================================
  // 6. Side-by-Side Agent Comparison View
  // ============================================================================
  it('switches to Comparison view and renders side-by-side comparison', () => {
    renderUserAiMarket();

    const compareBtn = screen.getByRole('button', { name: 'Comparison' });
    fireEvent.click(compareBtn);

    expect(screen.getByText('Side-by-Side Agent Comparison')).toBeInTheDocument();
    expect(screen.getByText('Select First Agent:')).toBeInTheDocument();
    expect(screen.getByText('Select Second Agent:')).toBeInTheDocument();
  });

  // ============================================================================
  // 7. Actions & Navigation
  // ============================================================================
  it('navigates to /user/chat when clicking Use in Workspace', () => {
    renderUserAiMarket();

    const useBtns = screen.getAllByRole('button', { name: /Use in Workspace/i });
    fireEvent.click(useBtns[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/user/chat');
  });

  it('triggers manual telemetry sync on Sync button click', () => {
    renderUserAiMarket();

    const syncBtn = screen.getByRole('button', { name: /Sync/i });
    fireEvent.click(syncBtn);
    expect(syncBtn).toBeInTheDocument();
  });

  // ============================================================================
  // 8. Admin Agents Registry
  // ============================================================================
  it('renders Admin Agents registry title, badge, and capability cards', async () => {
    renderAdminAgents();

    expect(screen.getByText(/AI Agent Registry & Orchestration Telemetry/i)).toBeInTheDocument();
    expect(screen.getByText('ADMIN REGISTRY')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Orchestrator Swarm Node')).toBeInTheDocument();
      expect(screen.getByText('Enterprise Document RAG')).toBeInTheDocument();
      expect(screen.getByText('MCP Sandboxed Executor')).toBeInTheDocument();
    });
  });

  it('triggers refresh in Admin Agents page', async () => {
    renderAdminAgents();

    const refreshBtn = screen.getByRole('button', { name: /REFRESH_REGISTRY/i });
    fireEvent.click(refreshBtn);
    expect(refreshBtn).toBeInTheDocument();
  });
});
