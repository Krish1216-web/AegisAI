import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import UserMcpMarket from '../pages/user/UserMcpMarket';
import AdminMcp from '../pages/admin/AdminMcp';
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

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockImplementation(() => Promise.resolve()),
  },
});

// Mock MCP API
vi.mock('../api/mcp', () => ({
  listMCPServers: vi.fn().mockResolvedValue({
    servers: [
      {
        id: 'srv-fs-01',
        name: 'Local Filesystem MCP Server',
        description: 'Filesystem daemon',
        server_url: 'stdio://filesystem-daemon',
        transport: 'stdio',
        status: 'active',
        enabled: true,
        protocol_version: '2024-11-05',
        capabilities_count: 3
      },
      {
        id: 'srv-pg-02',
        name: 'PostgreSQL Schema Inspector',
        description: 'Database metadata inspector',
        server_url: 'http://localhost:8001/mcp/stream',
        transport: 'streamable_http',
        status: 'active',
        enabled: true,
        protocol_version: '2024-11-05',
        capabilities_count: 2
      }
    ],
    total: 2
  }),
  listWorkspaceTools: vi.fn().mockResolvedValue({
    tools: [
      {
        id: 'tool-read-file',
        server_name: 'Local Filesystem MCP Server',
        server_transport: 'stdio',
        name: 'read_file',
        description: 'Reads files safely.',
        input_schema: {
          type: 'object',
          properties: { file_path: { type: 'string' } },
          required: ['file_path']
        },
        risk_level: 'safe',
        policy_decision: 'allow'
      },
      {
        id: 'tool-write-file',
        server_name: 'Local Filesystem MCP Server',
        server_transport: 'stdio',
        name: 'write_file',
        description: 'Writes files to disk.',
        input_schema: {
          type: 'object',
          properties: { file_path: { type: 'string' }, content: { type: 'string' } },
          required: ['file_path', 'content']
        },
        risk_level: 'restricted',
        policy_decision: 'require_confirmation',
        risk_reasons: ['Filesystem modification requires confirmation.']
      }
    ],
    total: 2
  }),
  listMCPResources: vi.fn().mockResolvedValue({ resources: [], total: 0 }),
  listMCPPrompts: vi.fn().mockResolvedValue({ prompts: [], total: 0 }),
  getMCPExecutionHistory: vi.fn().mockResolvedValue({ executions: [], total: 0 }),
  getMCPSecurityStatus: vi.fn().mockResolvedValue({ ssrf_protection: true }),
  getMCPSecurityAuditLog: vi.fn().mockResolvedValue({ logs: [] }),
  checkServerHealth: vi.fn().mockResolvedValue({ is_healthy: true, latency_ms: 18 }),
  refreshServerDiscovery: vi.fn().mockResolvedValue({ total_tools: 2, total_resources: 1, total_prompts: 1 }),
  generateToolConfirmationToken: vi.fn().mockResolvedValue({ token: 'test-conf-token' }),
  executeMCPTool: vi.fn().mockResolvedValue({
    execution_id: 'exec-test-01',
    tool_id: 'tool-read-file',
    tool_name: 'read_file',
    status: 'success',
    result: { status: 'success', data: 'Mock file content' },
    duration_ms: 45
  })
}));

// Mock platform API
vi.mock('../api/platform', () => ({
  getPlatformCapabilities: vi.fn().mockResolvedValue({
    total: 2,
    items: [
      { capability_id: 'mcp-fs-node', name: 'Filesystem Tool Daemon', description: 'Sandboxed I/O', workspace_scope: 'ws-prod-01' },
      { capability_id: 'mcp-sql-node', name: 'SQL Schema Engine', description: 'Readonly introspection', workspace_scope: null }
    ]
  })
}));

function renderUserMcpMarket(authOverrides = {}) {
  const defaultAuth = {
    isAuthenticated: true,
    token: 'test-token',
    user: { id: 'usr-admin-01', username: 'testadmin' },
    role: 'admin',
    workspaceId: 'ws-prod-01',
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    error: null,
    ...authOverrides
  };

  return render(
    <HashRouter>
      <ThemeProvider>
        <AuthContext.Provider value={defaultAuth}>
          <ToastProvider>
            <UserMcpMarket triggerNotification={vi.fn()} />
          </ToastProvider>
        </AuthContext.Provider>
      </ThemeProvider>
    </HashRouter>
  );
}

function renderAdminMcp() {
  return render(
    <HashRouter>
      <ThemeProvider>
        <AdminMcp addLog={vi.fn()} />
      </ThemeProvider>
    </HashRouter>
  );
}

describe('Phase 12.6 — MCP Center & Enterprise Integration Control Plane', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders MCP Center header, KPI overview strip, and tabs', async () => {
    renderUserMcpMarket();

    expect(screen.getByText('MCP Center')).toBeInTheDocument();
    expect(screen.getByText(/Connected Servers/i)).toBeInTheDocument();
    expect(screen.getByText(/Executable Tools/i)).toBeInTheDocument();
    expect(screen.getByText(/Exposed Resources/i)).toBeInTheDocument();
    expect(screen.getByText(/Transport Security/i)).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /Overview/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Servers/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tools/i })).toBeInTheDocument();
  });

  it('switches to Servers tab and filters servers by transport', async () => {
    renderUserMcpMarket();

    const serversTab = screen.getByRole('button', { name: /Servers/i });
    fireEvent.click(serversTab);

    expect(screen.getByText('Local Filesystem MCP Server')).toBeInTheDocument();
    expect(screen.getByText('PostgreSQL Schema Inspector')).toBeInTheDocument();

    const transportSelect = screen.getByDisplayValue(/All Transports/i);
    fireEvent.change(transportSelect, { target: { value: 'stdio' } });

    expect(screen.getByText('Local Filesystem MCP Server')).toBeInTheDocument();
    expect(screen.queryByText('PostgreSQL Schema Inspector')).not.toBeInTheDocument();
  });

  it('opens Server Inspector Drawer and pings health', async () => {
    renderUserMcpMarket();

    const serversTab = screen.getByRole('button', { name: /Servers/i });
    fireEvent.click(serversTab);

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/MCP Server Inspector/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Ping Server Health/i })).toBeInTheDocument();
    });

    const pingBtn = screen.getByRole('button', { name: /Ping Server Health/i });
    fireEvent.click(pingBtn);

    await waitFor(() => {
      expect(screen.getByText(/Health Check Passed/i)).toBeInTheDocument();
    });
  });

  it('switches to Tools tab and displays risk levels', async () => {
    renderUserMcpMarket();

    const toolsTab = screen.getByRole('button', { name: /Tools/i });
    fireEvent.click(toolsTab);

    await waitFor(() => {
      expect(screen.getByText('read_file')).toBeInTheDocument();
      expect(screen.getByText('write_file')).toBeInTheDocument();
      expect(screen.getByText('SAFE')).toBeInTheDocument();
      expect(screen.getByText('CONFIRMATION REQ')).toBeInTheDocument();
    });
  });

  it('executes safe tool and displays results', async () => {
    renderUserMcpMarket();

    const toolsTab = screen.getByRole('button', { name: /Tools/i });
    fireEvent.click(toolsTab);

    await waitFor(() => {
      expect(screen.getByText('read_file')).toBeInTheDocument();
    });

    const runButtons = screen.getAllByRole('button', { name: /Run Tool/i });
    fireEvent.click(runButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Run MCP Tool: read_file/i)).toBeInTheDocument();
    });

    const modal = screen.getByRole('dialog');
    const pathInput = within(modal).getByRole('textbox');
    fireEvent.change(pathInput, { target: { value: 'src/main.py' } });

    const executeBtn = within(modal).getByRole('button', { name: /Execute Tool/i });
    fireEvent.click(executeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Execution Completed/i)).toBeInTheDocument();
    });
  });

  it('requires operator confirmation for restricted tools', async () => {
    renderUserMcpMarket();

    const toolsTab = screen.getByRole('button', { name: /Tools/i });
    fireEvent.click(toolsTab);

    await waitFor(() => {
      expect(screen.getByText('write_file')).toBeInTheDocument();
    });

    // Click Run Tool for write_file (index 1)
    const runButtons = screen.getAllByRole('button', { name: /Run Tool/i });
    fireEvent.click(runButtons[1]);

    await waitFor(() => {
      expect(screen.getByText(/Restricted Tool Operation Warning/i)).toBeInTheDocument();
    });

    const modal = screen.getByRole('dialog');
    const textboxes = within(modal).getAllByRole('textbox');
    fireEvent.change(textboxes[0], { target: { value: 'output.txt' } });
    fireEvent.change(textboxes[1], { target: { value: 'Sample data' } });

    // Check confirmation checkbox
    const checkbox = within(modal).getByRole('checkbox');
    fireEvent.click(checkbox);

    const executeBtn = within(modal).getByRole('button', { name: /Execute Tool/i });
    fireEvent.click(executeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Execution Completed/i)).toBeInTheDocument();
    });
  });

  it('opens Connect New MCP Server modal and registers a server', async () => {
    renderUserMcpMarket();

    const addBtn = screen.getByRole('button', { name: /Add MCP Server/i });
    fireEvent.click(addBtn);

    expect(screen.getByText(/Connect New MCP Server/i)).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/GitHub Repository Inspector/i);
    fireEvent.change(nameInput, { target: { value: 'Internal Analytics Daemon' } });

    const urlInput = screen.getByPlaceholderText(/http:\/\/localhost:8001/i);
    fireEvent.change(urlInput, { target: { value: 'http://localhost:9000/mcp' } });

    const submitBtn = screen.getByRole('button', { name: /Connect Server/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Server Registered/i)).toBeInTheDocument();
    });
  });

  it('prompts disconnect server modal and confirms removal', async () => {
    renderUserMcpMarket();

    const serversTab = screen.getByRole('button', { name: /Servers/i });
    fireEvent.click(serversTab);

    const deleteButtons = screen.getAllByTitle('Disconnect Server');
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText(/Disconnect MCP Server/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm Disconnect/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Server Disconnected/i)).toBeInTheDocument();
    });
  });

  it('renders Resources, Prompts, Execution History, and Security tabs', () => {
    renderUserMcpMarket();

    // Resources Tab
    const resTab = screen.getByRole('button', { name: /Resources/i });
    fireEvent.click(resTab);
    expect(screen.getByText(/Exposed MCP Resources/i)).toBeInTheDocument();

    // Prompts Tab
    const promptsTab = screen.getByRole('button', { name: /Prompts/i });
    fireEvent.click(promptsTab);
    expect(screen.getByText(/Parameterizable Prompt Templates/i)).toBeInTheDocument();

    // History Tab
    const histTab = screen.getByRole('button', { name: /Execution History/i });
    fireEvent.click(histTab);
    expect(screen.getByText(/Live Tool Execution Stream/i)).toBeInTheDocument();

    // Security Tab
    const secTab = screen.getByRole('button', { name: /Security & Governance/i });
    fireEvent.click(secTab);
    expect(screen.getByText(/Enterprise Tool Security Controls/i)).toBeInTheDocument();
    expect(screen.getByText(/SSRF & Private IP Blocking/i)).toBeInTheDocument();
  });

  it('triggers manual registry refresh', async () => {
    renderUserMcpMarket();

    const refreshBtn = screen.getByRole('button', { name: /Refresh Registry/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(screen.getByText(/Registry Refreshed/i)).toBeInTheDocument();
    });
  });

  it('renders Admin MCP page with platform capabilities', async () => {
    renderAdminMcp();

    expect(screen.getByText(/MCP Integration & Tool Governance/i)).toBeInTheDocument();
    expect(screen.getByText(/Active MCP Daemons/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('GitHub Repository Manager')).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL Enterprise DB Connector')).toBeInTheDocument();
    });
  });
});
