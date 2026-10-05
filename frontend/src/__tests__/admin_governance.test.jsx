import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import AdminDashboard from '../pages/admin/AdminDashboard';
import AdminUsers from '../pages/admin/AdminUsers';
import AdminAgents from '../pages/admin/AdminAgents';
import AdminMcp from '../pages/admin/AdminMcp';
import AdminSecurity from '../pages/admin/AdminSecurity';
import AdminAnalytics from '../pages/admin/AdminAnalytics';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthContext } from '../context/AuthContext';
import { ToastProvider } from '../context/ToastContext';

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

// Mock ResizeObserver
global.ResizeObserver = global.ResizeObserver || class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock ResponsiveContainer from recharts
vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div style={{ width: '500px', height: '300px' }}>{children}</div>
  };
});

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate
  };
});

// Mock Admin API
vi.mock('../api/admin', () => ({
  getAdminOverview: vi.fn().mockResolvedValue({
    total_users: 142,
    active_users: 128,
    suspended_users: 3,
    total_workspaces: 12,
    active_workspaces: 10,
    total_executions: 15420,
    successful_executions: 15380,
    failed_executions: 40,
    cancelled_executions: 0,
    active_capabilities: 9,
    active_mcp_servers: 6,
    active_workflows: 8,
    avg_latency_ms: 124,
    success_rate: 99.7,
    system_status: 'HEALTHY',
    alerts_count: 2,
    security_alerts_count: 2,
    time_window: '24h'
  }),
  getAdminSystemHealth: vi.fn().mockResolvedValue({
    overall_status: 'HEALTHY',
    timestamp: Date.now(),
    environment: 'production',
    subsystems: [
      { name: 'Database (PostgreSQL + pgvector)', status: 'ONLINE', latency_ms: 4, details: {} },
      { name: 'Cache & Message Broker (Redis)', status: 'ONLINE', latency_ms: 1, details: {} },
      { name: 'Execution Worker Pool', status: 'ONLINE', latency_ms: 0, details: {} },
      { name: 'LLM Gateway (Gemini 2.5 Pro)', status: 'ONLINE', latency_ms: 120, details: {} }
    ]
  }),
  getAdminActivityFeed: vi.fn().mockResolvedValue({
    total: 2,
    events: [
      { event_id: 'act-1', summary: 'Agent Orgs initialized', user_id: 'usr-1', actor: 'alice@enterprise.com', event_type: 'AGENT_DEPLOY', timestamp: '2026-10-05T12:00:00Z', source_component: 'agent_engine', payload: {} },
      { event_id: 'act-2', summary: 'Postgres MCP connector attached', user_id: 'usr-2', actor: 'bob@enterprise.com', event_type: 'MCP_CONNECT', timestamp: '2026-10-05T11:45:00Z', source_component: 'mcp_gateway', payload: {} }
    ]
  }),
  getAdminUsers: vi.fn().mockImplementation((params = {}) => {
    const allUsers = [
      {
        id: 'usr-1',
        username: 'Alice Johnson',
        email: 'alice@enterprise.com',
        role: 'admin',
        is_active: true,
        is_verified: true,
        is_deleted: false,
        created_at: '2026-01-15T08:00:00Z',
        last_activity: '2026-10-05T11:00:00Z',
        workspaces_count: 4,
        workspaces: []
      },
      {
        id: 'usr-2',
        username: 'Bob Smith',
        email: 'bob@enterprise.com',
        role: 'member',
        is_active: true,
        is_verified: true,
        is_deleted: false,
        created_at: '2026-03-20T10:00:00Z',
        last_activity: '2026-10-04T15:30:00Z',
        workspaces_count: 2,
        workspaces: []
      },
      {
        id: 'usr-3',
        username: 'Charlie Suspended',
        email: 'charlie@enterprise.com',
        role: 'viewer',
        is_active: false,
        is_verified: true,
        is_deleted: false,
        created_at: '2026-05-10T14:00:00Z',
        last_activity: '2026-09-01T09:00:00Z',
        workspaces_count: 1,
        workspaces: []
      }
    ];
    let filtered = [...allUsers];
    if (params.search) {
      const s = params.search.toLowerCase();
      filtered = filtered.filter(u => u.username.toLowerCase().includes(s) || u.email.toLowerCase().includes(s));
    }
    if (params.role) {
      filtered = filtered.filter(u => u.role.toLowerCase() === params.role.toLowerCase());
    }
    if (params.is_active !== undefined) {
      filtered = filtered.filter(u => u.is_active === params.is_active);
    }
    return Promise.resolve({
      users: filtered,
      total: filtered.length,
      page: params.page || 1,
      page_size: params.page_size || 10
    });
  }),
  getAdminUserDetail: vi.fn().mockImplementation((userId) => Promise.resolve({
    id: userId,
    username: userId === 'usr-1' ? 'Alice Johnson' : 'Bob Smith',
    email: userId === 'usr-1' ? 'alice@enterprise.com' : 'bob@enterprise.com',
    role: userId === 'usr-1' ? 'admin' : 'member',
    is_active: true,
    is_verified: true,
    is_deleted: false,
    created_at: '2026-01-15T08:00:00Z',
    settings: {},
    workspaces: [{ workspace_id: 'ws-1', workspace_name: 'Workspace Alpha', role: 'admin' }],
    recent_audit_logs: [
      { id: 'aud-1', action: 'USER_LOGIN', created_at: '2026-10-05T11:00:00Z', details: 'Successful SSO login' }
    ]
  })),
  updateAdminUserStatus: vi.fn().mockResolvedValue({ message: 'User status updated', user_id: 'usr-1', is_active: false }),
  updateAdminUserRole: vi.fn().mockResolvedValue({ message: 'Role updated', user_id: 'usr-2', role: 'admin' }),
  getAdminRolesPermissions: vi.fn().mockResolvedValue({
    roles: [
      { id: 'r1', name: 'admin', description: 'Workspace administrator', users_count: 4 },
      { id: 'r2', name: 'member', description: 'Standard active member', users_count: 120 }
    ],
    permission_matrix: [],
    capability_permissions: []
  }),
  getAdminSecurityPosture: vi.fn().mockResolvedValue({
    tenant_isolation_enforced: true,
    rbac_posture: 'Strict Role-Based Access Control',
    confirmation_gate_active: true,
    ssrf_defense_active: true,
    secret_redaction_active: true,
    total_security_denials: 0,
    recent_denials: [],
    recent_alerts: []
  }),
  getAdminSecurityAlerts: vi.fn().mockResolvedValue({
    total: 2,
    alerts: [
      {
        alert_id: 'al-01',
        title: 'High Frequency Tool Invocations',
        rule_name: 'RATE_LIMIT_RULE',
        severity: 'HIGH',
        source: 'Agent Security Gateway',
        status: 'investigating',
        created_at: '2026-10-05T09:30:00Z',
        last_triggered_at: '2026-10-05T09:30:00Z',
        trigger_count: 12,
        description: 'Exceeded 500 tool calls/min rate threshold.'
      },
      {
        alert_id: 'al-02',
        title: 'Non-Standard MCP Handshake',
        rule_name: 'MCP_SCHEMA_MISMATCH',
        severity: 'WARNING',
        source: 'MCP Control Plane',
        status: 'resolved',
        created_at: '2026-10-05T08:15:00Z',
        last_triggered_at: '2026-10-05T08:15:00Z',
        trigger_count: 1,
        description: 'Payload schema mismatch on stdio handshake.'
      }
    ]
  }),
  verifyAdminAuditIntegrity: vi.fn().mockResolvedValue({
    chain_valid: true,
    total_records_checked: 4892,
    broken_links_count: 0,
    tampered_record_ids: [],
    tenant_id: 'tenant-enterprise-01',
    verified_at: '2026-10-05T12:00:00Z',
    details: 'Every audit record hash matches previous link signatures.'
  }),
  getAdminAuditLogs: vi.fn().mockResolvedValue({
    logs: [
      {
        id: 'log-101',
        actor: 'alice@enterprise.com',
        action: 'AGENT_DEPLOY',
        resource_type: 'agent',
        resource_id: 'agent-data-analyst',
        ip_address: '192.168.1.50',
        status: 'SUCCESS',
        hash: 'a1b2c3d4e5f6',
        created_at: '2026-10-05T11:50:00Z'
      },
      {
        id: 'log-102',
        actor: 'system',
        action: 'MCP_TOOL_EXECUTE',
        resource_type: 'mcp_tool',
        resource_id: 'github_search_issues',
        ip_address: '127.0.0.1',
        status: 'SUCCESS',
        hash: 'f6e5d4c3b2a1',
        created_at: '2026-10-05T11:45:00Z'
      }
    ],
    total: 2,
    page: 1,
    page_size: 10
  }),
  exportAdminReport: vi.fn().mockResolvedValue({
    content: '{"export":"valid"}',
    format: 'json',
    record_count: 24,
    generated_at: '2026-10-05T12:05:00Z'
  })
}));

// Mock Platform API
vi.mock('../api/platform', () => ({
  getPlatformCapabilities: vi.fn().mockResolvedValue({
    items: [
      {
        capability_id: 'agent_orchestrator',
        name: 'Orchestrator Agent',
        category: 'core',
        enabled: true,
        version: '2.0',
        required_permissions: ['agent:orchestrate', 'workspace:read']
      }
    ]
  }),
  getPlatformOverviewMetrics: vi.fn().mockResolvedValue({
    total_executions: 48920,
    success_rate: 99.4,
    avg_duration_ms: 142,
    p95_duration_ms: 380,
    failed_executions: 28,
    denied_executions: 4
  }),
  getPlatformCapabilityAnalytics: vi.fn().mockResolvedValue({
    capabilities: [
      {
        name: 'Document Extraction',
        total_executions: 12400,
        avg_duration_ms: 220,
        success_rate: 99.1,
        failed_executions: 12
      },
      {
        name: 'MCP Remote Tool Execution',
        total_executions: 24800,
        avg_duration_ms: 85,
        success_rate: 99.8,
        failed_executions: 5
      }
    ]
  }),
  getPlatformFailureAnalytics: vi.fn().mockResolvedValue({
    failures: [
      { failure_category: 'Timeout Exceeded', occurrence_count: 14 },
      { failure_category: 'Tool Schema Error', occurrence_count: 8 },
      { failure_category: 'Policy Denial', occurrence_count: 4 }
    ]
  }),
  getPlatformIntelligenceAnalytics: vi.fn().mockResolvedValue({
    avg_confidence: 0.965,
    avg_adaptive_attempts: 1.2,
    planning_decompositions: 8400
  })
}));

const mockAuthContext = {
  user: {
    id: 'usr-admin-1',
    name: 'Super Admin',
    email: 'admin@aegisai.enterprise',
    role: 'super_admin'
  },
  token: 'mock-admin-token',
  isAuthenticated: true,
  hasPermission: () => true
};

const renderWithProviders = (ui) => {
  return render(
    <ThemeProvider>
      <ToastProvider>
        <AuthContext.Provider value={mockAuthContext}>
          {ui}
        </AuthContext.Provider>
      </ToastProvider>
    </ThemeProvider>
  );
};

describe('PHASE 12.9 — Enterprise Governance & Control Center', () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AdminDashboard (Governance Mission Control)', () => {
    it('renders mission control title and KPI cards', async () => {
      renderWithProviders(<AdminDashboard />);

      expect(screen.getByText(/Enterprise Governance & Control Center/i)).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText(/128/i)).toBeInTheDocument(); // active users
        expect(screen.getByText(/15,420/i)).toBeInTheDocument(); // total executions
      });
    });

    it('renders the attention center items when warnings or issues exist', async () => {
      renderWithProviders(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Governance & Security Attention Center/i)).toBeInTheDocument();
        expect(screen.getByText(/High Frequency Tool Invocations/i)).toBeInTheDocument();
      });
    });

    it('renders the Subsystem Health Matrix with component statuses', async () => {
      renderWithProviders(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Subsystem Health & Dependency Diagnostics/i)).toBeInTheDocument();
        expect(screen.getByText(/Database/i)).toBeInTheDocument();
        expect(screen.getByText(/Cache & Message Broker/i)).toBeInTheDocument();
      });
    });

    it('renders live activity feed stream', async () => {
      renderWithProviders(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Recent Administrative & Execution Activity/i)).toBeInTheDocument();
        expect(screen.getByText(/Agent Orgs initialized/i)).toBeInTheDocument();
      });
    });
  });

  describe('AdminUsers (Identity & Access Governance)', () => {
    it('renders user list with role and status indicators', async () => {
      renderWithProviders(<AdminUsers />);

      await waitFor(() => {
        expect(screen.getByText(/Alice Johnson/i)).toBeInTheDocument();
        expect(screen.getByText(/Bob Smith/i)).toBeInTheDocument();
        expect(screen.getByText(/Charlie Suspended/i)).toBeInTheDocument();
      });
    });

    it('filters user list by search query', async () => {
      renderWithProviders(<AdminUsers />);

      await waitFor(() => {
        expect(screen.getByText(/Alice Johnson/i)).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search users/i);
      fireEvent.change(searchInput, { target: { value: 'Bob' } });

      const searchBtn = screen.getByRole('button', { name: /^Search$/i });
      fireEvent.click(searchBtn);

      await waitFor(() => {
        expect(screen.getByText(/Bob Smith/i)).toBeInTheDocument();
        expect(screen.queryByText(/Alice Johnson/i)).not.toBeInTheDocument();
      });
    });

    it('opens suspension modal and requires rationale before submitting', async () => {
      const { updateAdminUserStatus } = await import('../api/admin');
      renderWithProviders(<AdminUsers />);

      await waitFor(() => {
        expect(screen.getByText(/Alice Johnson/i)).toBeInTheDocument();
      });

      // Find suspend button for Alice
      const suspendButtons = screen.getAllByRole('button', { name: /^Suspend$/i });
      fireEvent.click(suspendButtons[0]);

      // Verify suspension modal is visible
      expect(screen.getByText(/Suspend Enterprise User/i)).toBeInTheDocument();
      expect(screen.getByText(/Mandatory Suspension Reason/i)).toBeInTheDocument();

      const confirmBtn = screen.getByRole('button', { name: /Confirm Suspension/i });
      expect(confirmBtn).toBeDisabled();

      // Enter rationale
      const reasonInput = screen.getByPlaceholderText(/Enter mandatory administrative rationale for compliance audit logging/i);
      fireEvent.change(reasonInput, { target: { value: 'Security violation under SOC-2 policy 4.2' } });

      expect(confirmBtn).not.toBeDisabled();
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(updateAdminUserStatus).toHaveBeenCalledWith('usr-1', false, 'Security violation under SOC-2 policy 4.2');
      });
    });

    it('opens User Inspector Drawer when clicking inspect', async () => {
      renderWithProviders(<AdminUsers />);

      const inspectButtons = await screen.findAllByRole('button', { name: /Inspect User/i });
      fireEvent.click(inspectButtons[0]);

      expect(await screen.findByText(/User Governance Inspector/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Effective Permissions/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('AdminAgents (Workforce Governance)', () => {
    it('renders canonical agent workforce cards with roles and categories', async () => {
      renderWithProviders(<AdminAgents />);

      await waitFor(() => {
        expect(screen.getByText(/AI Workforce & Agent Governance/i)).toBeInTheDocument();
        // Check for canonical agents
        expect(screen.getByText(/Orchestrator Agent/i)).toBeInTheDocument();
        expect(screen.getByText(/Planner Agent/i)).toBeInTheDocument();
        expect(screen.getByText(/Critic Agent/i)).toBeInTheDocument();
      });
    });

    it('filters workforce by category pills', async () => {
      renderWithProviders(<AdminAgents />);

      await waitFor(() => {
        expect(screen.getByText(/Orchestrator Agent/i)).toBeInTheDocument();
      });

      const verifyFilter = screen.getByRole('button', { name: /Verification/i });
      fireEvent.click(verifyFilter);

      expect(screen.getByText(/Critic Agent/i)).toBeInTheDocument();
      expect(screen.queryByText(/Orchestrator Agent/i)).not.toBeInTheDocument();
    });

    it('opens Agent Policy Inspector drawer when clicking Inspect', async () => {
      renderWithProviders(<AdminAgents />);

      await waitFor(() => {
        expect(screen.getByText(/Orchestrator Agent/i)).toBeInTheDocument();
      });

      const inspectButtons = screen.getAllByRole('button', { name: /Inspect Policies/i });
      fireEvent.click(inspectButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Agent Governance & Policy Inspector/i)).toBeInTheDocument();
        expect(screen.getByText(/Allowed Internal & MCP Tools/i)).toBeInTheDocument();
      });
    });
  });

  describe('AdminMcp (MCP Control Plane Governance)', () => {
    it('renders connected MCP server directory with protocol badges', async () => {
      renderWithProviders(<AdminMcp />);

      await waitFor(() => {
        expect(screen.getByText(/MCP Integration & Tool Governance/i)).toBeInTheDocument();
        expect(screen.getByText(/GitHub Repository Manager/i)).toBeInTheDocument();
        expect(screen.getByText(/PostgreSQL Enterprise DB Connector/i)).toBeInTheDocument();
      });
    });

    it('masks credentials safely with zero-knowledge indicator', async () => {
      renderWithProviders(<AdminMcp />);

      await waitFor(() => {
        expect(screen.getAllByText(/Configured & Encrypted/i).length).toBeGreaterThan(0);
      });
    });

    it('opens MCP server inspector drawer to view tool policy gating', async () => {
      renderWithProviders(<AdminMcp />);

      await waitFor(() => {
        expect(screen.getByText(/PostgreSQL Enterprise DB Connector/i)).toBeInTheDocument();
      });

      const inspectButtons = screen.getAllByRole('button', { name: /Inspect Server/i });
      fireEvent.click(inspectButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/MCP Server Governance Inspector/i)).toBeInTheDocument();
        expect(screen.getByText(/Introspected Tool Roster/i)).toBeInTheDocument();
      });
    });
  });

  describe('AdminSecurity (SOC Operations & Cryptographic Audit)', () => {
    it('renders SOC posture score and compliance indicators', async () => {
      renderWithProviders(<AdminSecurity />);

      await waitFor(() => {
        expect(screen.getByText(/Security Operations & Cryptographic Audit Center/i)).toBeInTheDocument();
        expect(screen.getByText(/Tenant Workspace Isolation/i)).toBeInTheDocument();
        expect(screen.getByText(/SSRF & Path Traversal Defense/i)).toBeInTheDocument();
      });
    });

    it('renders live security alerts tab and views alert details', async () => {
      renderWithProviders(<AdminSecurity />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Live Security Alerts/i })).toBeInTheDocument();
      });

      const alertsTabBtn = screen.getByRole('button', { name: /Live Security Alerts/i });
      fireEvent.click(alertsTabBtn);

      await waitFor(() => {
        expect(screen.getByText(/High Frequency Tool Invocations/i)).toBeInTheDocument();
        expect(screen.getByText(/Non-Standard MCP Handshake/i)).toBeInTheDocument();
      });
    });

    it('executes cryptographic SHA-256 audit log integrity verification', async () => {
      const { verifyAdminAuditIntegrity } = await import('../api/admin');
      renderWithProviders(<AdminSecurity />);

      await waitFor(() => {
        expect(screen.getByText(/Active Security Defenses & Gates/i)).toBeInTheDocument();
      });

      const verifyBtn = screen.getByRole('button', { name: /Verify Audit Chain/i });
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(verifyAdminAuditIntegrity).toHaveBeenCalled();
        expect(screen.getByText(/Audit Chain Cryptographically Valid/i)).toBeInTheDocument();
      });
    });

    it('opens and submits compliance report export modal', async () => {
      const { exportAdminReport } = await import('../api/admin');
      renderWithProviders(<AdminSecurity />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Export Report/i })).toBeInTheDocument();
      });

      const exportBtn = screen.getByRole('button', { name: /Export Report/i });
      fireEvent.click(exportBtn);

      expect(screen.getByText(/Export Compliance Audit Report/i)).toBeInTheDocument();

      const downloadBtn = screen.getByRole('button', { name: /Download Report/i });
      fireEvent.click(downloadBtn);

      await waitFor(() => {
        expect(exportAdminReport).toHaveBeenCalled();
      });
    });
  });

  describe('AdminAnalytics (System Telemetry & Performance)', () => {
    it('renders platform telemetry metrics and time window selector', async () => {
      renderWithProviders(<AdminAnalytics />);

      expect(screen.getByText(/Platform Telemetry & Performance Analytics/i)).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText(/48,920/i)).toBeInTheDocument(); // executions
        expect(screen.getByText(/142 ms/i)).toBeInTheDocument(); // avg latency
        expect(screen.getByText(/96.5%/i)).toBeInTheDocument(); // confidence
      });
    });

    it('allows changing time window to 7d and triggers re-fetch', async () => {
      const { getPlatformOverviewMetrics } = await import('../api/platform');
      renderWithProviders(<AdminAnalytics />);

      await waitFor(() => {
        expect(screen.getByText(/48,920/i)).toBeInTheDocument();
      });

      const button7d = screen.getByRole('button', { name: /7d/i });
      fireEvent.click(button7d);

      await waitFor(() => {
        expect(getPlatformOverviewMetrics).toHaveBeenCalledWith('7d');
      });
    });

    it('renders capability performance matrix and failure breakdown', async () => {
      renderWithProviders(<AdminAnalytics />);

      await waitFor(() => {
        expect(screen.getByText(/Capability Execution Volume/i)).toBeInTheDocument();
        expect(screen.getByText(/Failure Root-Cause Distribution/i)).toBeInTheDocument();
        expect(screen.getByText(/Capability Performance & Reliability Matrix/i)).toBeInTheDocument();
        expect(screen.getByText(/Document Extraction/i)).toBeInTheDocument();
      });
    });
  });

});
