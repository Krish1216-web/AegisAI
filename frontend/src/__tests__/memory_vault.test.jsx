import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HashRouter } from 'react-router-dom';
import UserMemory from '../pages/user/UserMemory';
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

// Mock knowledge graph API
vi.mock('../api/knowledgeGraph', () => ({
  syncMemoryToGraph: vi.fn().mockResolvedValue({
    memory_id: 'mem-vec-001',
    status: 'synced',
    nodes_synced_count: 2,
    edges_synced_count: 2,
    latency_ms: 12.5
  })
}));

function renderUserMemory(authOverrides = {}) {
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
            <UserMemory triggerNotification={vi.fn()} />
          </ToastProvider>
        </AuthContext.Provider>
      </ThemeProvider>
    </HashRouter>
  );
}

describe('Phase 12.5 — Memory Vault & Long-Term Intelligence Center', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Memory Vault header, KPIs, and canonical context records', () => {
    renderUserMemory();

    expect(screen.getByText('Memory Vault')).toBeInTheDocument();
    expect(screen.getByText(/Total Long-Term Context/i)).toBeInTheDocument();
    expect(screen.getByText(/Vector Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/Knowledge Graph Sync/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Tenant Isolation/i).length).toBeGreaterThan(0);

    // Verify canonical memories present
    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
    expect(screen.getByText(/Active workspace uses PostgreSQL 16/i)).toBeInTheDocument();
    expect(screen.getByText(/AegisAI autonomous multi-agent system/i)).toBeInTheDocument();
  });

  it('filters memories by category pills', () => {
    renderUserMemory();

    // Click on User Preference category
    const userPrefBtn = screen.getByRole('button', { name: /User Preference/i });
    fireEvent.click(userPrefBtn);

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
    expect(screen.queryByText(/Active workspace uses PostgreSQL 16/i)).not.toBeInTheDocument();

    // Click on System Knowledge category
    const sysKnowBtn = screen.getByRole('button', { name: /System Knowledge/i });
    fireEvent.click(sysKnowBtn);

    expect(screen.getByText(/Model Context Protocol \(MCP\) tool servers/i)).toBeInTheDocument();
    expect(screen.queryByText(/Operator prefers FastAPI/i)).not.toBeInTheDocument();

    // Click back on All Categories
    const allBtn = screen.getByRole('button', { name: /All Categories/i });
    fireEvent.click(allBtn);

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
  });

  it('searches memories by query text and clears search', () => {
    renderUserMemory();

    const searchInput = screen.getByPlaceholderText(/Search cognitive memory/i);
    fireEvent.change(searchInput, { target: { value: 'PostgreSQL' } });

    expect(screen.getByText(/Active workspace uses PostgreSQL 16/i)).toBeInTheDocument();
    expect(screen.queryByText(/Operator prefers FastAPI/i)).not.toBeInTheDocument();

    // Clear search
    const clearBtn = screen.getByLabelText('Clear search');
    fireEvent.click(clearBtn);

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
    expect(screen.getByText(/Active workspace uses PostgreSQL 16/i)).toBeInTheDocument();
  });

  it('displays empty state when search finds no match and clears filters', () => {
    renderUserMemory();

    const searchInput = screen.getByPlaceholderText(/Search cognitive memory/i);
    fireEvent.change(searchInput, { target: { value: 'nonexistent-pattern-xyz' } });

    expect(screen.getByText(/No Memories Match Query/i)).toBeInTheDocument();

    const clearFiltersBtn = screen.getByRole('button', { name: /Clear Search Filters/i });
    fireEvent.click(clearFiltersBtn);

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
  });

  it('switches between Directory, Table View, and Graph Entity Matrix', () => {
    renderUserMemory();

    // Switch to Table View
    const tableBtn = screen.getByRole('button', { name: /Table View/i });
    fireEvent.click(tableBtn);

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('mem-vec-001')).toBeInTheDocument();

    // Switch to Graph Matrix View
    const matrixBtn = screen.getByRole('button', { name: /Graph Entity Matrix/i });
    fireEvent.click(matrixBtn);

    expect(screen.getByText(/Knowledge Graph Association Matrix/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Resolved Graph Nodes/i).length).toBeGreaterThan(0);

    // Switch back to Directory Grid
    const dirBtn = screen.getByRole('button', { name: /Directory Grid/i });
    fireEvent.click(dirBtn);

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();
  });

  it('opens inspector drawer and displays full metadata, metrics, and agent access', async () => {
    renderUserMemory();

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Cognitive Memory Inspector/i)).toBeInTheDocument();
      expect(screen.getByText(/Scrubbed Memory Content/i)).toBeInTheDocument();
      expect(screen.getByText(/Importance Rating/i)).toBeInTheDocument();
      expect(screen.getByText(/Confidence Score/i)).toBeInTheDocument();
      expect(screen.getByText(/Authorized Consumer Agents/i)).toBeInTheDocument();
      expect(screen.getByText(/Knowledge Graph Layer/i)).toBeInTheDocument();
    });
  });

  it('copies memory content to clipboard from inspector drawer', async () => {
    renderUserMemory();

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Copy Content/i)).toBeInTheDocument();
    });

    const copyBtn = screen.getByRole('button', { name: /Copy Content/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalled();
  });

  it('triggers Knowledge Graph sync for a memory in drawer', async () => {
    renderUserMemory();

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Re-sync Knowledge Graph/i)).toBeInTheDocument();
    });

    const syncBtn = screen.getByRole('button', { name: /Re-sync Knowledge Graph/i });
    fireEvent.click(syncBtn);

    await waitFor(() => {
      expect(screen.getByText(/Knowledge Graph Synced/i)).toBeInTheDocument();
    });
  });

  it('opens Add Memory Context modal and stores a new memory item', async () => {
    renderUserMemory();

    const addBtn = screen.getByRole('button', { name: /Add Memory Context/i });
    fireEvent.click(addBtn);

    expect(screen.getByText(/Add Long-Term Context Memory/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/Operator prefers async FastAPI/i);
    fireEvent.change(textarea, { target: { value: 'Operator mandates strict unit test coverage on all endpoints.' } });

    const submitBtn = screen.getByRole('button', { name: /Store Memory Record/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Context Memory Added/i)).toBeInTheDocument();
      expect(screen.getByText(/Operator mandates strict unit test coverage/i)).toBeInTheDocument();
    });
  });

  it('prompts delete modal and removes a memory upon confirmation', async () => {
    renderUserMemory();

    // Switch to table view to access direct trash button
    const tableBtn = screen.getByRole('button', { name: /Table View/i });
    fireEvent.click(tableBtn);

    const deleteBtn = screen.getByLabelText('Delete memory mem-vec-001');
    fireEvent.click(deleteBtn);

    expect(screen.getByText(/Confirm permanent removal of this memory record/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm Delete/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Memory Deleted/i)).toBeInTheDocument();
      expect(screen.queryByText('mem-vec-001')).not.toBeInTheDocument();
    });
  });

  it('exports memory context JSON file on export button click', () => {
    const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/test-blob');
    const revokeObjectURLMock = vi.fn();
    global.URL.createObjectURL = createObjectURLMock;
    global.URL.revokeObjectURL = revokeObjectURLMock;

    renderUserMemory();

    const exportBtn = screen.getByRole('button', { name: /Export JSON/i });
    fireEvent.click(exportBtn);

    expect(createObjectURLMock).toHaveBeenCalled();
  });

  it('triggers manual telemetry sync on sync button click', async () => {
    renderUserMemory();

    const syncBtn = screen.getByRole('button', { name: /Sync Telemetry/i });
    fireEvent.click(syncBtn);

    await waitFor(() => {
      expect(screen.getByText(/Memory Vault Refreshed/i)).toBeInTheDocument();
    });
  });

  it('sorts memories by confidence and timestamps', () => {
    renderUserMemory();

    const sortSelect = screen.getByDisplayValue(/Importance \(High to Low\)/i);
    fireEvent.change(sortSelect, { target: { value: 'confidence_desc' } });

    expect(screen.getByText(/Operator prefers FastAPI/i)).toBeInTheDocument();

    fireEvent.change(sortSelect, { target: { value: 'newest' } });
    expect(screen.getByText(/Current workspace operator session/i)).toBeInTheDocument();
  });

  it('navigates to Knowledge Graph when clicking View in Graph', () => {
    renderUserMemory();

    const matrixBtn = screen.getByRole('button', { name: /Graph Entity Matrix/i });
    fireEvent.click(matrixBtn);

    const viewInGraphBtns = screen.getAllByRole('button', { name: /View in Graph/i });
    fireEvent.click(viewInGraphBtns[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/user/graph');
  });
});
