import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HashRouter } from 'react-router-dom';

import {
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  MetricCard,
  Input,
  Textarea,
  Select,
  Checkbox,
  Switch,
  Modal,
  ConfirmDialog,
  Drawer,
  Tabs,
  EmptyState,
  Skeleton,
  Spinner,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Pagination,
  Breadcrumb,
  CodeBlock,
  Timeline
} from '../components/ui';

import { ThemeProvider, useTheme } from '../context/ThemeContext';
import { ToastProvider, useToast } from '../context/ToastContext';

// Helper component for Theme testing
function ThemeConsumer() {
  const { theme, toggleTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme-val">{theme}</span>
      <button onClick={toggleTheme}>Toggle</button>
      <button onClick={() => setTheme('light')}>SetLight</button>
    </div>
  );
}

// Helper component for Toast testing
function ToastConsumer() {
  const { success, error, info } = useToast();
  return (
    <div>
      <button onClick={() => success('Save Successful', 'Entity was persisted')}>TriggerSuccess</button>
      <button onClick={() => error('Save Failed', 'Validation error occurred')}>TriggerError</button>
      <button onClick={() => info('Notice', 'System updated')}>TriggerInfo</button>
    </div>
  );
}

describe('Phase 12.1 Enterprise Design System Components', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  // ============================================================================
  // 1. Button & IconButton Tests
  // ============================================================================
  it('renders Button with primary variant and handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Execute Agent</Button>);

    const btn = screen.getByRole('button', { name: /execute agent/i });
    expect(btn).toBeDefined();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders Button in loading state with spinner and disabled behavior', () => {
    const handleClick = vi.fn();
    render(<Button isLoading onClick={handleClick}>Processing</Button>);

    const btn = screen.getByRole('button');
    expect(btn.disabled).toBe(true);
    fireEvent.click(btn);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('renders IconButton with accessible aria-label and click listener', () => {
    const handleClick = vi.fn();
    render(<IconButton aria-label="Settings Menu" onClick={handleClick} icon={<span>⚙</span>} />);

    const btn = screen.getByRole('button', { name: /settings menu/i });
    expect(btn).toBeDefined();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  // ============================================================================
  // 2. Badge & StatusBadge Tests
  // ============================================================================
  it('renders Badge with default and custom variants', () => {
    render(<Badge variant="success">PRODUCTION_READY</Badge>);
    expect(screen.getByText('PRODUCTION_READY')).toBeDefined();
  });

  it('normalizes execution and job statuses in StatusBadge', () => {
    const { rerender } = render(<StatusBadge status="running" />);
    expect(screen.getByText('RUNNING')).toBeDefined();

    rerender(<StatusBadge status="completed" />);
    expect(screen.getByText('COMPLETED')).toBeDefined();

    rerender(<StatusBadge status="failed" />);
    expect(screen.getByText('FAILED')).toBeDefined();

    rerender(<StatusBadge status="queued" />);
    expect(screen.getByText('QUEUED')).toBeDefined();
  });

  // ============================================================================
  // 3. Card & MetricCard Tests
  // ============================================================================
  it('renders Card with Header, Title, and Content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Memory Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Total items: 450</p>
        </CardContent>
      </Card>
    );

    expect(screen.getByText('Memory Statistics')).toBeDefined();
    expect(screen.getByText('Total items: 450')).toBeDefined();
  });

  it('renders MetricCard with trend metrics and values', () => {
    render(
      <MetricCard
        title="Active Workflows"
        value="48"
        trend={{ direction: 'up', value: '+14%', label: 'vs last week' }}
      />
    );

    expect(screen.getByText('Active Workflows')).toBeDefined();
    expect(screen.getByText('48')).toBeDefined();
    expect(screen.getByText('+14%')).toBeDefined();
  });

  // ============================================================================
  // 4. Form Controls (Input, Textarea, Select, Checkbox, Switch) Tests
  // ============================================================================
  it('renders Input with label, required marker, helper text, and handles changes', () => {
    const handleChange = vi.fn();
    render(
      <Input
        label="Agent Name"
        required
        helperText="Enter a unique identifier for this agent"
        onChange={handleChange}
        placeholder="researcher-agent"
      />
    );

    expect(screen.getByText('Agent Name')).toBeDefined();
    expect(screen.getByText('Enter a unique identifier for this agent')).toBeDefined();
    
    const input = screen.getByPlaceholderText('researcher-agent');
    fireEvent.change(input, { target: { value: 'rag-agent' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders Input in error state with validation message', () => {
    render(<Input label="API Key" error="Invalid cryptographic signature" />);
    expect(screen.getByText('Invalid cryptographic signature')).toBeDefined();
  });

  it('renders Textarea and Select with options', () => {
    const options = [
      { value: 'gpt-4o', label: 'OpenAI GPT-4o' },
      { value: 'claude-3-5-sonnet', label: 'Anthropic Claude 3.5' }
    ];

    render(
      <div>
        <Textarea label="Prompt Instruction" defaultValue="Analyze the code" />
        <Select label="Model Selection" options={options} />
      </div>
    );

    expect(screen.getByText('Prompt Instruction')).toBeDefined();
    expect(screen.getByText('Model Selection')).toBeDefined();
    expect(screen.getByText('Anthropic Claude 3.5')).toBeDefined();
  });

  it('handles Checkbox and Switch toggle state transitions', () => {
    const handleCheckbox = vi.fn();
    const handleSwitch = vi.fn();

    render(
      <div>
        <Checkbox label="Enable Multi-Hop Reasoning" onChange={handleCheckbox} />
        <Switch label="Strict Tenant Isolation" onChange={handleSwitch} />
      </div>
    );

    const checkbox = screen.getByRole('checkbox', { name: /enable multi-hop reasoning/i });
    fireEvent.click(checkbox);
    expect(handleCheckbox).toHaveBeenCalledWith(true);

    const toggle = screen.getByRole('switch', { name: /strict tenant isolation/i });
    fireEvent.click(toggle);
    expect(handleSwitch).toHaveBeenCalledWith(true);
  });

  // ============================================================================
  // 5. Modal & ConfirmDialog Tests
  // ============================================================================
  it('renders Modal when isOpen=true and responds to close trigger', () => {
    const handleClose = vi.fn();
    const { rerender } = render(
      <Modal isOpen={false} onClose={handleClose} title="Configure MCP Server">
        <p>Modal body content</p>
      </Modal>
    );

    expect(screen.queryByText('Configure MCP Server')).toBeNull();

    rerender(
      <Modal isOpen={true} onClose={handleClose} title="Configure MCP Server">
        <p>Modal body content</p>
      </Modal>
    );

    expect(screen.getByText('Configure MCP Server')).toBeDefined();
    expect(screen.getByText('Modal body content')).toBeDefined();

    const closeBtn = screen.getByRole('button', { name: /close dialog/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders ConfirmDialog and handles confirmation for destructive actions', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Knowledge Base"
        message="All vector points will be purged permanently."
        confirmLabel="Purge Base"
        onConfirm={handleConfirm}
        onClose={handleCancel}
      />
    );

    expect(screen.getByText('Delete Knowledge Base')).toBeDefined();
    expect(screen.getByText('All vector points will be purged permanently.')).toBeDefined();

    const confirmBtn = screen.getByRole('button', { name: /purge base/i });
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  // ============================================================================
  // 6. Drawer, Tabs, and EmptyState Tests
  // ============================================================================
  it('renders Drawer when open and handles escape key', () => {
    const handleClose = vi.fn();
    render(
      <Drawer isOpen={true} onClose={handleClose} title="Execution Evidence">
        <p>Evidence payload details</p>
      </Drawer>
    );

    expect(screen.getByText('Execution Evidence')).toBeDefined();
    expect(screen.getByText('Evidence payload details')).toBeDefined();

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalled();
  });

  it('renders Tabs and handles tab selection', () => {
    const handleTabChange = vi.fn();
    const tabs = [
      { id: 'overview', label: 'Overview', badge: 3 },
      { id: 'logs', label: 'Execution Logs' },
      { id: 'security', label: 'Security Audits' }
    ];

    render(<Tabs tabs={tabs} activeTab="overview" onChange={handleTabChange} />);

    expect(screen.getByText('Overview')).toBeDefined();
    expect(screen.getByText('Execution Logs')).toBeDefined();

    const logsTab = screen.getByRole('tab', { name: /execution logs/i });
    fireEvent.click(logsTab);
    expect(handleTabChange).toHaveBeenCalledWith('logs');
  });

  it('renders EmptyState with call-to-action button', () => {
    const handleAction = vi.fn();
    render(
      <EmptyState
        title="No documents uploaded"
        description="Upload PDFs or Markdown files to index knowledge."
        actionLabel="Upload First Document"
        onAction={handleAction}
      />
    );

    expect(screen.getByText('No documents uploaded')).toBeDefined();
    expect(screen.getByText('Upload PDFs or Markdown files to index knowledge.')).toBeDefined();

    const actionBtn = screen.getByRole('button', { name: /upload first document/i });
    fireEvent.click(actionBtn);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  // ============================================================================
  // 7. Table & Pagination Tests
  // ============================================================================
  it('renders Table and handles pagination navigation', () => {
    const handlePageChange = vi.fn();
    render(
      <div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Agent</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Researcher</TableCell>
              <TableCell>Active</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <Pagination currentPage={2} totalPages={5} totalItems={50} pageSize={10} onPageChange={handlePageChange} />
      </div>
    );

    expect(screen.getByText('Researcher')).toBeDefined();
    expect(screen.getByText('Active')).toBeDefined();
    expect(screen.getByText(/Page 2 of 5/i)).toBeDefined();

    const nextBtn = screen.getByRole('button', { name: /next page/i });
    fireEvent.click(nextBtn);
    expect(handlePageChange).toHaveBeenCalledWith(3);
  });

  // ============================================================================
  // 8. Breadcrumb, CodeBlock, Timeline Tests
  // ============================================================================
  it('renders Breadcrumb hierarchy with links', () => {
    const items = [
      { label: 'Workspaces', to: '/workspaces' },
      { label: 'Engineering' }
    ];

    render(
      <HashRouter>
        <Breadcrumb items={items} />
      </HashRouter>
    );

    expect(screen.getByText('Workspaces')).toBeDefined();
    expect(screen.getByText('Engineering')).toBeDefined();
  });

  it('renders CodeBlock with formatted code', () => {
    const sampleJson = { agent_id: 'ag-01', status: 'READY' };
    render(<CodeBlock code={sampleJson} language="json" title="Manifest Output" />);

    expect(screen.getByText('Manifest Output')).toBeDefined();
    expect(screen.getByText(/ag-01/i)).toBeDefined();
  });

  it('renders Timeline with sequential steps and status badges', () => {
    const steps = [
      { id: '1', title: 'Parse Document', description: 'Chunking PDF stream', status: 'COMPLETED', timestamp: '10:00:01' },
      { id: '2', title: 'Generate Embeddings', description: 'Computing 1536-dim vectors', status: 'RUNNING', timestamp: '10:00:03' }
    ];

    render(<Timeline steps={steps} currentStepIndex={1} />);

    expect(screen.getByText('Parse Document')).toBeDefined();
    expect(screen.getByText('Chunking PDF stream')).toBeDefined();
    expect(screen.getByText('Generate Embeddings')).toBeDefined();
    expect(screen.getByText('COMPLETED')).toBeDefined();
  });

  // ============================================================================
  // 9. Theme & Toast Context Integration Tests
  // ============================================================================
  it('persists and toggles themes via ThemeProvider', () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    const themeDisplay = screen.getByTestId('theme-val');
    expect(themeDisplay.textContent).toBe('dark');

    const toggleBtn = screen.getByRole('button', { name: /toggle/i });
    fireEvent.click(toggleBtn);
    expect(themeDisplay.textContent).toBe('light');
    expect(localStorage.getItem('aegis_theme')).toBe('light');
  });

  it('triggers and displays notification toasts via ToastProvider', () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    const successBtn = screen.getByRole('button', { name: /triggersuccess/i });
    fireEvent.click(successBtn);

    expect(screen.getByText('Save Successful')).toBeDefined();
    expect(screen.getByText('Entity was persisted')).toBeDefined();
  });
});
