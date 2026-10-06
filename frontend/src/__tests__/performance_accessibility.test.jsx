import React, { useState } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import {
  ErrorBoundary,
  Modal,
  ConfirmDialog,
  Drawer,
  Tabs,
  Input,
  Textarea,
  Select,
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Card,
  MetricCard,
  EmptyState,
  Skeleton,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Pagination,
  Switch,
  Checkbox,
  Breadcrumb,
  CodeBlock,
} from '../components/ui';
import CommandPalette from '../components/CommandPalette';
import { ToastProvider, useToast } from '../context/ToastContext';
import { ThemeProvider } from '../context/ThemeContext';
import { MemoryRouter } from 'react-router-dom';

// Helper component that throws an error for ErrorBoundary testing
function ProblemChild({ shouldThrow = true, message = 'Simulated module failure' }) {
  if (shouldThrow) {
    throw new Error(message);
  }
  return <div>Child Component Healthy</div>;
}

// Helper component for ToastProvider testing
function ToastTestConsumer() {
  const { success, error, warning, info } = useToast();
  return (
    <div>
      <button onClick={() => success('Save Complete', 'Data persisted successfully.')}>
        Trigger Success
      </button>
      <button onClick={() => error('Auth Failure', 'Access denied to target resource.')}>
        Trigger Error
      </button>
      <button onClick={() => warning('Quota Warning', 'Resource quota at 90%.')}>
        Trigger Warning
      </button>
      <button onClick={() => info('Status Sync', 'System telemetry refreshed.')}>
        Trigger Info
      </button>
    </div>
  );
}

describe('Phase 12.10 — Performance, Accessibility & Resilience Engineering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  // ==========================================================================
  // 1. ErrorBoundary Resilience Tests
  // ==========================================================================
  describe('1. ErrorBoundary Resilience & Component Isolation', () => {
    it('renders child components cleanly when no exception occurs', () => {
      render(
        <ErrorBoundary>
          <div>Safe Content Output</div>
        </ErrorBoundary>
      );
      expect(screen.getByText('Safe Content Output')).toBeInTheDocument();
    });

    it('intercepts rendering errors and displays accessible recovery alert', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <ErrorBoundary title="Isolated Module Shield">
          <ProblemChild message="Vector index corrupted" />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Isolated Module Shield')).toBeInTheDocument();
      expect(screen.getByText('Vector index corrupted')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();

      spy.mockRestore();
    });

    it('supports inline variant for embedded sub-surfaces', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <ErrorBoundary variant="inline" title="Chart Render Failed">
          <ProblemChild message="Canvas WebGL context lost" />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Chart Render Failed')).toBeInTheDocument();
      expect(screen.getByText('Canvas WebGL context lost')).toBeInTheDocument();

      spy.mockRestore();
    });

    it('invokes onError callback with error metadata', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const onErrorMock = vi.fn();

      render(
        <ErrorBoundary onError={onErrorMock}>
          <ProblemChild message="Telemetry stream closed unexpectedly" />
        </ErrorBoundary>
      );

      expect(onErrorMock).toHaveBeenCalledTimes(1);
      expect(onErrorMock.mock.calls[0][0].message).toBe('Telemetry stream closed unexpectedly');

      spy.mockRestore();
    });

    it('supports custom fallback function with reset capability', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      function FallbackComponent({ error, resetErrorBoundary }) {
        return (
          <div role="alert">
            <p>Custom Error: {error.message}</p>
            <button onClick={resetErrorBoundary}>Custom Reset</button>
          </div>
        );
      }

      render(
        <ErrorBoundary fallback={FallbackComponent}>
          <ProblemChild message="Custom engine error" />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Custom Error: Custom engine error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Custom Reset' })).toBeInTheDocument();

      spy.mockRestore();
    });
  });

  // ==========================================================================
  // 2. Modal & ConfirmDialog Accessibility Tests
  // ==========================================================================
  describe('2. Modal & ConfirmDialog Focus Management & Accessibility', () => {
    it('renders with role="dialog", aria-modal="true", and aria-labelledby', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="System Configuration">
          <p>Configuration Body</p>
        </Modal>
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
      expect(screen.getByText('System Configuration')).toHaveAttribute('id', 'modal-title');
    });

    it('dismisses modal on Escape key press', () => {
      const onClose = vi.fn();
      render(
        <Modal isOpen={true} onClose={onClose} title="Inspect Node">
          <button>Action</button>
        </Modal>
      );

      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('locks body scroll when opened and restores on unmount', () => {
      const { unmount } = render(
        <Modal isOpen={true} onClose={vi.fn()} title="Scroll Lock Test">
          <p>Body</p>
        </Modal>
      );

      expect(document.body.style.overflow).toBe('hidden');
      unmount();
      expect(document.body.style.overflow).toBe('');
    });

    it('renders ConfirmDialog with accessible confirmation and destructive options', () => {
      const onConfirm = vi.fn();
      const onClose = vi.fn();

      render(
        <ConfirmDialog
          isOpen={true}
          onClose={onClose}
          onConfirm={onConfirm}
          title="Revoke Node Certificate"
          message="This action will revoke the cryptographic token permanently."
          confirmLabel="Revoke Certificate"
          isDestructive={true}
        />
      );

      expect(screen.getByText('Revoke Node Certificate')).toBeInTheDocument();
      expect(screen.getByText(/revoke the cryptographic token permanently/i)).toBeInTheDocument();

      const confirmBtn = screen.getByRole('button', { name: 'Revoke Certificate' });
      fireEvent.click(confirmBtn);
      expect(onConfirm).toHaveBeenCalledTimes(1);

      const cancelBtn = screen.getByRole('button', { name: 'Cancel' });
      fireEvent.click(cancelBtn);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('disables cancel and indicates loading in ConfirmDialog when isLoading is true', () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          title="Flushing Vector DB"
          isLoading={true}
        />
      );

      const cancelBtn = screen.getByRole('button', { name: 'Cancel' });
      expect(cancelBtn).toBeDisabled();
    });
  });

  // ==========================================================================
  // 3. Drawer Accessibility & Focus Trapping Tests
  // ==========================================================================
  describe('3. Drawer Slide-Over Accessibility & Focus Trapping', () => {
    it('renders with role="dialog", aria-modal="true", and aria-labelledby="drawer-title"', () => {
      render(
        <Drawer isOpen={true} onClose={vi.fn()} title="Agent Policy Inspector">
          <p>Policy Rules</p>
        </Drawer>
      );

      const drawer = screen.getByRole('dialog');
      expect(drawer).toBeInTheDocument();
      expect(drawer).toHaveAttribute('aria-modal', 'true');
      expect(drawer).toHaveAttribute('aria-labelledby', 'drawer-title');
      expect(screen.getByText('Agent Policy Inspector')).toHaveAttribute('id', 'drawer-title');
    });

    it('closes Drawer when Escape key is pressed', () => {
      const onClose = vi.fn();
      render(
        <Drawer isOpen={true} onClose={onClose} title="Memory Inspector">
          <p>Memory Dump</p>
        </Drawer>
      );

      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('does not render markup when isOpen is false', () => {
      render(
        <Drawer isOpen={false} onClose={vi.fn()} title="Closed Drawer">
          <p>Hidden Content</p>
        </Drawer>
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.queryByText('Closed Drawer')).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. Tabs Keyboard Navigation & WAI-ARIA Tests
  // ==========================================================================
  describe('4. Tabs Keyboard Arrow Navigation & WAI-ARIA Compliance', () => {
    const testTabs = [
      { id: 'overview', label: 'Overview' },
      { id: 'capabilities', label: 'Capabilities', badge: '9' },
      { id: 'policies', label: 'Policies' },
      { id: 'audit', label: 'Audit Stream' },
    ];

    it('renders tablist with role="tablist" and accessible role="tab" buttons', () => {
      render(<Tabs tabs={testTabs} activeTab="overview" onChange={vi.fn()} />);

      expect(screen.getByRole('tablist')).toBeInTheDocument();
      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(4);
      expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
      expect(tabs[0]).toHaveAttribute('tabIndex', '0');
      expect(tabs[1]).toHaveAttribute('aria-selected', 'false');
      expect(tabs[1]).toHaveAttribute('tabIndex', '-1');
    });

    it('navigates to next tab on ArrowRight key press', () => {
      const onChange = vi.fn();
      render(<Tabs tabs={testTabs} activeTab="overview" onChange={onChange} />);

      const activeTab = screen.getByRole('tab', { name: /Overview/i });
      fireEvent.keyDown(activeTab, { key: 'ArrowRight' });

      expect(onChange).toHaveBeenCalledWith('capabilities');
    });

    it('navigates to previous tab on ArrowLeft key press with loop-around', () => {
      const onChange = vi.fn();
      render(<Tabs tabs={testTabs} activeTab="overview" onChange={onChange} />);

      const activeTab = screen.getByRole('tab', { name: /Overview/i });
      fireEvent.keyDown(activeTab, { key: 'ArrowLeft' });

      expect(onChange).toHaveBeenCalledWith('audit');
    });

    it('navigates to first tab on Home and last tab on End', () => {
      const onChange = vi.fn();
      render(<Tabs tabs={testTabs} activeTab="capabilities" onChange={onChange} />);

      const activeTab = screen.getByRole('tab', { name: /Capabilities/i });
      fireEvent.keyDown(activeTab, { key: 'Home' });
      expect(onChange).toHaveBeenCalledWith('overview');

      fireEvent.keyDown(activeTab, { key: 'End' });
      expect(onChange).toHaveBeenCalledWith('audit');
    });
  });

  // ==========================================================================
  // 5. Form Controls Accessibility Tests
  // ==========================================================================
  describe('5. Form Controls Accessibility & Error Descriptions', () => {
    it('associates Input label with input element via htmlFor and id', () => {
      render(<Input label="Workspace Name" id="ws-input" placeholder="e.g. Prod-East" />);

      const input = screen.getByLabelText(/Workspace Name/i);
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('id', 'ws-input');
    });

    it('links Input error message via aria-invalid="true" and aria-describedby', () => {
      render(
        <Input
          label="Server Endpoint"
          id="mcp-url"
          error="Valid HTTPS or SSE URL is required"
        />
      );

      const input = screen.getByLabelText(/Server Endpoint/i);
      expect(input).toHaveAttribute('aria-invalid', 'true');
      expect(input).toHaveAttribute('aria-describedby', 'mcp-url-error');

      const errorMsg = screen.getByRole('alert');
      expect(errorMsg).toHaveAttribute('id', 'mcp-url-error');
      expect(errorMsg).toHaveTextContent('Valid HTTPS or SSE URL is required');
    });

    it('links Input helperText via aria-describedby when error is absent', () => {
      render(
        <Input
          label="API Key Token"
          id="api-token"
          helperText="Zero-knowledge encrypted at rest."
        />
      );

      const input = screen.getByLabelText(/API Key Token/i);
      expect(input).toHaveAttribute('aria-invalid', 'false');
      expect(input).toHaveAttribute('aria-describedby', 'api-token-helper');
      expect(screen.getByText('Zero-knowledge encrypted at rest.')).toHaveAttribute('id', 'api-token-helper');
    });

    it('sets aria-required="true" and required on required Input', () => {
      render(<Input label="Tenant Identifier" required={true} />);

      const input = screen.getByLabelText(/Tenant Identifier/i);
      expect(input).toHaveAttribute('aria-required', 'true');
      expect(input).toBeRequired();
    });

    it('sets accessible error and helper attributes on Textarea and Select', () => {
      render(
        <>
          <Textarea label="Execution Rationale" id="rationale-text" error="Mandatory rationale required" />
          <Select label="Security Tier" id="sec-tier" options={[{ value: 'strict', label: 'Strict' }]} helperText="Applies enterprise RBAC" />
        </>
      );

      const textarea = screen.getByLabelText(/Execution Rationale/i);
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
      expect(textarea).toHaveAttribute('aria-describedby', 'rationale-text-error');

      const select = screen.getByLabelText(/Security Tier/i);
      expect(select).toHaveAttribute('aria-describedby', 'sec-tier-helper');
    });
  });

  // ==========================================================================
  // 6. Command Palette WAI-ARIA 1.2 Combobox Tests
  // ==========================================================================
  describe('6. Command Palette WAI-ARIA Combobox & Keyboard Navigation', () => {
    it('renders with role="dialog", combobox input, and listbox', () => {
      render(
        <MemoryRouter>
          <ThemeProvider>
            <CommandPalette onClose={vi.fn()} role="user" />
          </ThemeProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('dialog', { name: /Command Palette/i })).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('navigates command options using ArrowDown and ArrowUp', () => {
      render(
        <MemoryRouter>
          <ThemeProvider>
            <CommandPalette onClose={vi.fn()} role="user" />
          </ThemeProvider>
        </MemoryRouter>
      );

      const combobox = screen.getByRole('combobox');
      const options = screen.getAllByRole('option');

      expect(options[0]).toHaveAttribute('aria-selected', 'true');

      fireEvent.keyDown(combobox, { key: 'ArrowDown' });
      expect(options[1]).toHaveAttribute('aria-selected', 'true');

      fireEvent.keyDown(combobox, { key: 'ArrowUp' });
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });

    it('filters command list on search query update', () => {
      render(
        <MemoryRouter>
          <ThemeProvider>
            <CommandPalette onClose={vi.fn()} role="user" />
          </ThemeProvider>
        </MemoryRouter>
      );

      const combobox = screen.getByRole('combobox');
      fireEvent.change(combobox, { target: { value: 'Workflow' } });

      expect(screen.getByText('Open Workflow Builder')).toBeInTheDocument();
      expect(screen.queryByText('Open Memory Vault')).not.toBeInTheDocument();
    });

    it('closes on Escape key press', () => {
      const onClose = vi.fn();
      render(
        <MemoryRouter>
          <ThemeProvider>
            <CommandPalette onClose={onClose} role="user" />
          </ThemeProvider>
        </MemoryRouter>
      );

      const combobox = screen.getByRole('combobox');
      fireEvent.keyDown(combobox, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 7. Toast Notifications & Live Regions Tests
  // ==========================================================================
  describe('7. Toast Notifications & Live Regions', () => {
    it('announces error and warning toasts with role="alert"', () => {
      render(
        <ToastProvider>
          <ToastTestConsumer />
        </ToastProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Trigger Error' }));

      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
      expect(screen.getByText(/Auth Failure/i)).toBeInTheDocument();
      expect(screen.getByText('Access denied to target resource.')).toBeInTheDocument();
    });

    it('announces success and info toasts with role="status"', () => {
      render(
        <ToastProvider>
          <ToastTestConsumer />
        </ToastProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Trigger Success' }));

      const status = screen.getByRole('status');
      expect(status).toBeInTheDocument();
      expect(screen.getByText(/Save Complete/i)).toBeInTheDocument();
    });

    it('allows dismissing a toast notification manually', () => {
      render(
        <ToastProvider>
          <ToastTestConsumer />
        </ToastProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Trigger Info' }));
      expect(screen.getByText(/Status Sync/i)).toBeInTheDocument();

      const dismissBtn = screen.getByRole('button', { name: /Dismiss notification/i });
      fireEvent.click(dismissBtn);

      expect(screen.queryByText(/Status Sync/i)).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 8. Table & Pagination Accessibility Tests
  // ==========================================================================
  describe('8. Table & Pagination Accessibility', () => {
    it('renders accessible pagination buttons with ARIA labels and disabled states', () => {
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={1}
          totalPages={5}
          totalItems={50}
          pageSize={10}
          onPageChange={onPageChange}
        />
      );

      expect(screen.getByText((_, el) => el?.tagName.toLowerCase() === 'span' && /Showing.*1.*to.*10.*of.*50.*entries/i.test(el.textContent))).toBeInTheDocument();

      const firstBtn = screen.getByRole('button', { name: 'First page' });
      const prevBtn = screen.getByRole('button', { name: 'Previous page' });
      const nextBtn = screen.getByRole('button', { name: 'Next page' });
      const lastBtn = screen.getByRole('button', { name: 'Last page' });

      expect(firstBtn).toBeDisabled();
      expect(prevBtn).toBeDisabled();
      expect(nextBtn).toBeEnabled();
      expect(lastBtn).toBeEnabled();

      fireEvent.click(nextBtn);
      expect(onPageChange).toHaveBeenCalledWith(2);

      fireEvent.click(lastBtn);
      expect(onPageChange).toHaveBeenCalledWith(5);
    });

    it('renders structured semantic Table elements', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Identity</TableHead>
              <TableHead>Role</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Krish Patel</TableCell>
              <TableCell>System Admin</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('row')).toHaveLength(2);
      expect(screen.getByText('Krish Patel')).toBeInTheDocument();
      expect(screen.getByText('System Admin')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 9. Semantic Badges, Cards & Text Summaries Tests
  // ==========================================================================
  describe('9. Badges, Cards & Text Alternative Summaries', () => {
    it('renders StatusBadge with accessible semantic status text and indicator dot', () => {
      render(
        <>
          <StatusBadge status="ONLINE" category="system" />
          <StatusBadge status="FAILED" category="execution" />
          <StatusBadge status="BLOCKED" category="security" />
        </>
      );

      expect(screen.getByText('ONLINE')).toBeInTheDocument();
      expect(screen.getByText('FAILED')).toBeInTheDocument();
      expect(screen.getByText('BLOCKED')).toBeInTheDocument();
    });

    it('renders MetricCard with title, value, trend description, and subtitle', () => {
      render(
        <MetricCard
          title="Total Ingestion Volume"
          value="1,420"
          subtitle="99.4% vector indexing rate"
          trend="+12.5% vs baseline"
        />
      );

      expect(screen.getByText('Total Ingestion Volume')).toBeInTheDocument();
      expect(screen.getByText('1,420')).toBeInTheDocument();
      expect(screen.getByText('99.4% vector indexing rate')).toBeInTheDocument();
      expect(screen.getByText('+12.5% vs baseline')).toBeInTheDocument();
    });

    it('renders EmptyState with accessible icon, title, description, and action button', () => {
      const onAction = vi.fn();
      render(
        <EmptyState
          title="No Documents Indexed"
          description="Upload PDF or Markdown files to initialize vector embeddings."
          actionLabel="Upload Document"
          onAction={onAction}
        />
      );

      expect(screen.getByText('No Documents Indexed')).toBeInTheDocument();
      expect(screen.getByText(/Upload PDF or Markdown files/i)).toBeInTheDocument();

      const btn = screen.getByRole('button', { name: 'Upload Document' });
      fireEvent.click(btn);
      expect(onAction).toHaveBeenCalledTimes(1);
    });

    it('renders Skeleton placeholders for progressive layout loading without layout shift', () => {
      render(
        <div data-testid="skeleton-container">
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="card" height={100} />
          <Skeleton variant="circle" width={40} height={40} />
        </div>
      );

      expect(screen.getByTestId('skeleton-container').children).toHaveLength(3);
    });
  });

  // ==========================================================================
  // 10. Buttons & Interactive Targets Accessibility Tests
  // ==========================================================================
  describe('10. Buttons & Touch Target Accessibility', () => {
    it('supports keyboard focus and click dispatch on Button', () => {
      const onClick = vi.fn();
      render(<Button onClick={onClick}>Execute DAG</Button>);

      const btn = screen.getByRole('button', { name: 'Execute DAG' });
      btn.focus();
      expect(btn).toHaveFocus();

      fireEvent.click(btn);
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('renders IconButton with accessible aria-label and touch target sizing', () => {
      const onClick = vi.fn();
      render(
        <IconButton
          icon={<span>⚙</span>}
          ariaLabel="Configure Node Engine"
          onClick={onClick}
          size="md"
        />
      );

      const btn = screen.getByRole('button', { name: 'Configure Node Engine' });
      expect(btn).toHaveAttribute('aria-label', 'Configure Node Engine');

      fireEvent.click(btn);
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('shows accessible spinner when Button isLoading is true and disables interactions', () => {
      const onClick = vi.fn();
      render(
        <Button isLoading={true} onClick={onClick}>
          Save Settings
        </Button>
      );

      const btn = screen.getByRole('button');
      expect(btn).toBeDisabled();
      fireEvent.click(btn);
      expect(onClick).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 11. Switch, Checkbox, Breadcrumb & CodeBlock Accessibility Tests
  // ==========================================================================
  describe('11. Switch, Checkbox, Breadcrumb & CodeBlock Accessibility', () => {
    it('renders Switch with role="switch" and aria-checked', () => {
      const onChange = vi.fn();
      render(
        <Switch
          checked={true}
          onChange={onChange}
          label="Auto-Indexing Mode"
          description="Vectorize chunks automatically"
        />
      );

      const switchInput = screen.getByRole('switch');
      expect(switchInput).toBeInTheDocument();
      expect(switchInput).toBeChecked();
      expect(switchInput).toHaveAttribute('aria-checked', 'true');
      expect(screen.getByText('Auto-Indexing Mode')).toBeInTheDocument();
      expect(screen.getByText('Vectorize chunks automatically')).toBeInTheDocument();
    });

    it('renders Checkbox with accessible labeling and state', () => {
      const onChange = vi.fn();
      render(
        <Checkbox
          checked={false}
          onChange={onChange}
          label="Enable SSRF Shield"
        />
      );

      const chk = screen.getByRole('checkbox', { name: /Enable SSRF Shield/i });
      expect(chk).not.toBeChecked();

      fireEvent.click(chk);
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it('renders Breadcrumb with aria-label="Breadcrumb" and navigable items', () => {
      render(
        <MemoryRouter>
          <Breadcrumb
            items={[
              { label: 'Workspaces', to: '/user/workspaces' },
              { label: 'Platform Engine' },
            ]}
          />
        </MemoryRouter>
      );

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' });
      expect(nav).toBeInTheDocument();
      expect(screen.getByText('Workspaces')).toBeInTheDocument();
      expect(screen.getByText('Platform Engine')).toBeInTheDocument();
    });

    it('renders CodeBlock with copy button having accessible label', () => {
      render(
        <CodeBlock
          code={{ status: 'ONLINE', nodes: 7 }}
          language="json"
          title="Cluster State"
        />
      );

      expect(screen.getByText('Cluster State')).toBeInTheDocument();
      const copyBtn = screen.getByRole('button', { name: /Copy code to clipboard/i });
      expect(copyBtn).toBeInTheDocument();
    });
  });
});
