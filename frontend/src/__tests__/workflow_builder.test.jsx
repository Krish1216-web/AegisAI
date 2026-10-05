import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import UserWorkflows from '../pages/user/UserWorkflows';
import UserWorkflowEditor from '../pages/user/UserWorkflowEditor';
import UserWorkflowSchedules from '../pages/user/UserWorkflowSchedules';
import UserWorkflowApprovals from '../pages/user/UserWorkflowApprovals';
import UserWorkflowAnalytics from '../pages/user/UserWorkflowAnalytics';
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

// Mock ResizeObserver for ReactFlow / XYFlow
global.ResizeObserver = global.ResizeObserver || class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ workflowId: 'wf-test-01' })
  };
});

// Mock workflows API
vi.mock('../api/workflows', () => ({
  getWorkflows: vi.fn().mockResolvedValue({
    workflows: [
      {
        id: 'wf-test-01',
        name: 'Autonomous Research Pipeline',
        description: 'Multi-step research and intelligence gathering DAG.',
        status: 'active',
        version: 2,
        is_active: true,
        node_count: 4,
        edge_count: 3,
        updated_at: '2026-10-05T14:00:00Z'
      },
      {
        id: 'wf-test-02',
        name: 'Daily Security Triage',
        description: 'Automated triage and alert categorization.',
        status: 'draft',
        version: 1,
        is_active: false,
        node_count: 2,
        edge_count: 1,
        updated_at: '2026-10-04T12:00:00Z'
      }
    ],
    total: 2
  }),
  getWorkflow: vi.fn().mockResolvedValue({
    id: 'wf-test-01',
    name: 'Autonomous Research Pipeline',
    description: 'Multi-step research and intelligence gathering DAG.',
    status: 'active',
    version: 2,
    nodes: [
      { id: 'n1', name: 'Start Trigger', node_key: 'start_1', node_type: 'start' },
      { id: 'n2', name: 'Research Agent', node_key: 'agent_research', node_type: 'agent' },
      { id: 'n3', name: 'Data Formatter', node_key: 'transform_1', node_type: 'transform' },
      { id: 'n4', name: 'Final Output', node_key: 'end_1', node_type: 'end' }
    ],
    edges: [
      { id: 'e1', source_node_id: 'n1', target_node_id: 'n2' },
      { id: 'e2', source_node_id: 'n2', target_node_id: 'n3' },
      { id: 'e3', source_node_id: 'n3', target_node_id: 'n4' }
    ],
    variables: [{ name: 'env_name', value: 'Production', value_type: 'string', is_secret: false }]
  }),
  getWorkflowDefinition: vi.fn().mockResolvedValue({
    id: 'wf-test-01',
    name: 'Autonomous Research Pipeline',
    description: 'Multi-step research and intelligence gathering DAG.',
    status: 'active',
    version: 2,
    nodes: [
      {
        id: 'n1',
        name: 'Start Trigger',
        node_key: 'start_1',
        node_type: 'start',
        position: { x: 50, y: 150 },
        config: {}
      },
      {
        id: 'n2',
        name: 'Research Agent',
        node_key: 'agent_research',
        node_type: 'agent',
        position: { x: 280, y: 150 },
        config: { agent_name: 'Research Agent' }
      }
    ],
    edges: [
      { id: 'e1', source_node_id: 'n1', target_node_id: 'n2', priority: 1 }
    ],
    variables: [{ name: 'env_name', value: 'Production', value_type: 'string', is_secret: false }]
  }),
  createWorkflow: vi.fn().mockResolvedValue({
    id: 'wf-created-03',
    name: 'Competitive Intel Pipeline',
    description: 'Automated multi-step processing workflow.',
    status: 'draft',
    version: 1
  }),
  updateWorkflow: vi.fn().mockResolvedValue({ status: 'active' }),
  updateWorkflowDefinition: vi.fn().mockResolvedValue({
    id: 'wf-test-01',
    name: 'Autonomous Research Pipeline',
    version: 3,
    status: 'active'
  }),
  cloneWorkflow: vi.fn().mockResolvedValue({
    id: 'wf-cloned-04',
    name: 'Autonomous Research Pipeline (Copy)',
    version: 1,
    status: 'draft'
  }),
  deleteWorkflow: vi.fn().mockResolvedValue(undefined),
  validateWorkflow: vi.fn().mockResolvedValue({
    valid: true,
    errors: [],
    warnings: []
  }),
  activateWorkflow: vi.fn().mockResolvedValue({ status: 'active' }),
  pauseWorkflow: vi.fn().mockResolvedValue({ status: 'paused' }),
  archiveWorkflow: vi.fn().mockResolvedValue({ status: 'archived' }),
  executeWorkflow: vi.fn().mockResolvedValue({
    id: 'exec-run-101',
    workflow_id: 'wf-test-01',
    status: 'completed',
    output_data: { result: 'Research analysis completed with 4 insights.' }
  }),
  getWorkflowExecutions: vi.fn().mockResolvedValue([
    {
      id: 'exec-run-101',
      workflow_id: 'wf-test-01',
      status: 'completed',
      created_at: '2026-10-05T14:30:00Z',
      started_at: '2026-10-05T14:30:01Z'
    }
  ]),
  getWorkflowExecution: vi.fn().mockResolvedValue({
    id: 'exec-run-101',
    workflow_id: 'wf-test-01',
    status: 'completed',
    output_data: { result: 'Success' },
    execution_nodes: [
      { node_key: 'start_1', status: 'completed' },
      { node_key: 'agent_research', status: 'completed' }
    ]
  }),
  cancelWorkflowExecution: vi.fn().mockResolvedValue({ id: 'exec-run-101', status: 'cancelled' }),
  approveWorkflowExecution: vi.fn().mockResolvedValue({ id: 'exec-run-101', status: 'running' }),
  getWorkflowApprovals: vi.fn().mockResolvedValue({
    approvals: [
      {
        id: 'app-01',
        title: 'Production Write Authorization',
        status: 'pending',
        policy: 'manual',
        required_count: 1,
        created_at: '2026-10-05T15:00:00Z'
      }
    ],
    total: 1
  }),
  approveWorkflowApproval: vi.fn().mockResolvedValue({ id: 'app-01', status: 'approved' }),
  rejectWorkflowApproval: vi.fn().mockResolvedValue({ id: 'app-01', status: 'rejected' }),
  getWorkflowSchedules: vi.fn().mockResolvedValue({
    schedules: [
      {
        id: 'sched-01',
        name: 'Nightly Intelligence Ingestion',
        cron_expression: '0 2 * * *',
        timezone: 'Asia/Kolkata',
        status: 'active',
        is_enabled: true,
        total_runs: 28,
        failure_count: 0
      }
    ],
    total: 1
  }),
  createWorkflowSchedule: vi.fn().mockResolvedValue({ id: 'sched-02', name: 'Hourly Scan' }),
  pauseWorkflowSchedule: vi.fn().mockResolvedValue({ status: 'paused' }),
  resumeWorkflowSchedule: vi.fn().mockResolvedValue({ status: 'active' }),
  deleteWorkflowSchedule: vi.fn().mockResolvedValue(undefined),
  triggerWorkflowSchedule: vi.fn().mockResolvedValue({ id: 'exec-sched-01', status: 'running' }),
  getWorkflowAnalyticsOverview: vi.fn().mockResolvedValue({ total_executions: 142, success_rate: 98.4 }),
  getWorkflowAnalyticsPerformance: vi.fn().mockResolvedValue({ items: [] }),
  getWorkflowAnalyticsNodes: vi.fn().mockResolvedValue({ items: [] }),
  getWorkflowAnalyticsFailures: vi.fn().mockResolvedValue({ items: [] }),
  getWorkflowAnalyticsComposition: vi.fn().mockResolvedValue({}),
  getWorkflowAnalyticsSchedules: vi.fn().mockResolvedValue({}),
  getWorkflowAnalyticsApprovals: vi.fn().mockResolvedValue({})
}));

function renderWithProviders(ui) {
  const defaultAuth = {
    isAuthenticated: true,
    token: 'test-token',
    user: { id: 'usr-admin-01', username: 'testadmin' },
    role: 'admin',
    workspaceId: 'ws-prod-01',
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    error: null
  };

  return render(
    <HashRouter>
      <ThemeProvider>
        <AuthContext.Provider value={defaultAuth}>
          <ToastProvider>
            {ui}
          </ToastProvider>
        </AuthContext.Provider>
      </ThemeProvider>
    </HashRouter>
  );
}

describe('Phase 12.7 — Workflow Builder & Visual AI Automation Studio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Workflow Studio directory, header, and KPI metrics strip', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    expect(screen.getByText('Workflow Studio')).toBeInTheDocument();
    expect(screen.getByText(/Total Workflows/i)).toBeInTheDocument();
    expect(screen.getByText(/Active Automations/i)).toBeInTheDocument();
    expect(screen.getByText(/Draft \/ Paused/i)).toBeInTheDocument();
    expect(screen.getByText(/Orchestrated Nodes/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Daily Security Triage')).toBeInTheDocument();
    });
  });

  it('filters workflows by status dropdown and search query', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Daily Security Triage')).toBeInTheDocument();
    });

    const statusSelect = screen.getByDisplayValue(/All Statuses/i);
    fireEvent.change(statusSelect, { target: { value: 'active' } });

    expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    expect(screen.queryByText('Daily Security Triage')).not.toBeInTheDocument();
  });

  it('opens Create Workflow modal and initializes a template', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    const newBtn = screen.getByRole('button', { name: /New Workflow/i });
    fireEvent.click(newBtn);

    expect(screen.getByText(/Create New Workflow/i)).toBeInTheDocument();

    const modal = screen.getByRole('dialog');
    const nameInput = within(modal).getByPlaceholderText(/Multi-Agent Competitive Intelligence/i);
    fireEvent.change(nameInput, { target: { value: 'Competitive Intel Pipeline' } });

    const submitBtn = within(modal).getByRole('button', { name: /Initialize & Open Studio/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/user/workflows/wf-created-03');
    });
  });

  it('opens Run Execution modal and executes workflow run', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const runButtons = screen.getAllByRole('button', { name: /Run/i });
    fireEvent.click(runButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Execute Workflow:/i)).toBeInTheDocument();
    });

    const modal = screen.getByRole('dialog');
    const dispatchBtn = within(modal).getByRole('button', { name: /Dispatch Execution/i });
    fireEvent.click(dispatchBtn);

    await waitFor(() => {
      expect(within(modal).getByText(/Execution Status: completed/i)).toBeInTheDocument();
    });
  });

  it('opens Accessible Linear Plain-Text Outline modal', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const outlineButtons = screen.getAllByTitle('Accessible Text Outline');
    fireEvent.click(outlineButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Accessible Workflow Outline/i)).toBeInTheDocument();
      expect(screen.getByText(/1\. Start Trigger/i)).toBeInTheDocument();
      expect(screen.getByText(/2\. Research Agent/i)).toBeInTheDocument();
    });
  });

  it('prompts delete workflow modal and confirms deletion', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Delete Workflow');
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText(/Delete Workflow/i)).toBeInTheDocument();

    const modal = screen.getByRole('dialog');
    const confirmBtn = within(modal).getByRole('button', { name: /Confirm Delete/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.queryByText(/Confirm Delete/i)).not.toBeInTheDocument();
    });
  });

  it('switches to Pending Approvals, Automation Schedules, and Analytics tabs', async () => {
    renderWithProviders(<UserWorkflows triggerNotification={vi.fn()} />);

    // Approvals Tab
    const approvalsTab = screen.getByRole('button', { name: /Pending Approvals/i });
    fireEvent.click(approvalsTab);
    await waitFor(() => {
      expect(screen.getByText('Production Write Authorization')).toBeInTheDocument();
    });

    // Schedules Tab
    const schedulesTab = screen.getByRole('button', { name: /Automation Schedules/i });
    fireEvent.click(schedulesTab);
    await waitFor(() => {
      expect(screen.getByText('Nightly Intelligence Ingestion')).toBeInTheDocument();
    });

    // Analytics Tab
    const analyticsTab = screen.getByRole('button', { name: /Workflow Analytics/i });
    fireEvent.click(analyticsTab);
    expect(screen.getByText(/Workflow Analytics/i)).toBeInTheDocument();
  });

  it('renders UserWorkflowEditor with toolbar, node palette, canvas, and saves definition', async () => {
    renderWithProviders(<UserWorkflowEditor triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Node Palette')).toBeInTheDocument();
      expect(screen.getByText('Control Flow')).toBeInTheDocument();
      expect(screen.getByText('AI & Cognition')).toBeInTheDocument();
      expect(screen.getByText('MCP & Integrations')).toBeInTheDocument();
    });

    const saveBtn = screen.getByRole('button', { name: /Save/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });
  });

  it('validates graph topology in UserWorkflowEditor', async () => {
    renderWithProviders(<UserWorkflowEditor triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const validateBtn = screen.getByRole('button', { name: /Validate/i });
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(screen.getByText(/DAG Validation Passed/i)).toBeInTheDocument();
    });
  });

  it('opens Variables modal in UserWorkflowEditor and displays variables', async () => {
    renderWithProviders(<UserWorkflowEditor triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const varsBtn = screen.getByRole('button', { name: /Variables/i });
    fireEvent.click(varsBtn);

    await waitFor(() => {
      expect(screen.getByText('Workflow Variables')).toBeInTheDocument();
      expect(screen.getByDisplayValue('env_name')).toBeInTheDocument();
    });
  });

  it('opens accessible text outline from editor toolbar', async () => {
    renderWithProviders(<UserWorkflowEditor triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Research Pipeline')).toBeInTheDocument();
    });

    const outlineBtn = screen.getByTitle('Accessible Text Outline');
    fireEvent.click(outlineBtn);

    await waitFor(() => {
      expect(screen.getByText(/Accessible Workflow Outline/i)).toBeInTheDocument();
      expect(screen.getByText(/1\. Start Trigger/i)).toBeInTheDocument();
    });
  });

  it('approves and rejects requests in UserWorkflowApprovals', async () => {
    renderWithProviders(<UserWorkflowApprovals triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Production Write Authorization')).toBeInTheDocument();
    });

    const approveBtn = screen.getByRole('button', { name: /^Approve$/i });
    fireEvent.click(approveBtn);

    expect(screen.getByText(/Approve Workflow Gate/i)).toBeInTheDocument();
  });

  it('renders and manages schedules in UserWorkflowSchedules', async () => {
    renderWithProviders(<UserWorkflowSchedules triggerNotification={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Nightly Intelligence Ingestion')).toBeInTheDocument();
      expect(screen.getByText('Asia/Kolkata')).toBeInTheDocument();
    });

    const triggerBtn = screen.getByTitle('Trigger Run Now');
    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(screen.getByText('Nightly Intelligence Ingestion')).toBeInTheDocument();
    });
  });
});
