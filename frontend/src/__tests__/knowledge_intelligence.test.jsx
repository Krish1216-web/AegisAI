import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import UserDocuments from '../pages/user/UserDocuments';
import UserGraph from '../pages/user/UserGraph';
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

const mockNavigate = vi.fn();
let mockSearchParams = new URLSearchParams();
const mockSetSearchParams = vi.fn((params) => {
  mockSearchParams = new URLSearchParams(params);
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams, mockSetSearchParams]
  };
});

// Mock Documents API
vi.mock('../api/documents', () => ({
  listDocuments: vi.fn().mockResolvedValue([
    {
      id: 'doc-001',
      filename: 'architecture_specification_v2.pdf',
      file_type: 'pdf',
      file_size: 1048576,
      status: 'indexed',
      chunk_count: 24,
      entity_count: 18,
      relationship_count: 12,
      embedding_model: 'text-embedding-3-large',
      created_at: '2026-10-05T10:00:00Z',
      updated_at: '2026-10-05T10:05:00Z'
    },
    {
      id: 'doc-002',
      filename: 'security_compliance_soc2.docx',
      file_type: 'docx',
      file_size: 524288,
      status: 'processing',
      chunk_count: 12,
      entity_count: 6,
      relationship_count: 4,
      embedding_model: 'text-embedding-3-large',
      created_at: '2026-10-05T11:00:00Z',
      updated_at: '2026-10-05T11:02:00Z'
    }
  ]),
  getDocumentDetails: vi.fn().mockResolvedValue({
    id: 'doc-001',
    filename: 'architecture_specification_v2.pdf',
    file_type: 'pdf',
    file_size: 1048576,
    status: 'indexed',
    chunk_count: 24,
    entity_count: 18,
    relationship_count: 12,
    embedding_model: 'text-embedding-3-large',
    created_at: '2026-10-05T10:00:00Z',
    updated_at: '2026-10-05T10:05:00Z',
    metadata: { author: 'Engineering Team', classification: 'Confidential' }
  }),
  getDocumentStatus: vi.fn().mockResolvedValue({
    status: 'indexed',
    progress: 100,
    stage: 'completed'
  }),
  listDocumentChunks: vi.fn().mockResolvedValue([
    {
      id: 'chk-001',
      document_id: 'doc-001',
      chunk_index: 0,
      content: 'AegisAI utilizes an autonomous multi-agent orchestration architecture with dynamic subagent routing and sandboxed tool execution.',
      token_count: 64,
      similarity_score: 0.94,
      created_at: '2026-10-05T10:02:00Z'
    },
    {
      id: 'chk-002',
      document_id: 'doc-001',
      chunk_index: 1,
      content: 'Knowledge graph entity extraction leverages named-entity recognition and relation extraction over partitioned document chunks.',
      token_count: 58,
      similarity_score: 0.88,
      created_at: '2026-10-05T10:03:00Z'
    }
  ]),
  uploadDocument: vi.fn().mockResolvedValue({
    id: 'doc-003',
    filename: 'newly_uploaded.pdf',
    status: 'pending'
  }),
  deleteDocument: vi.fn().mockResolvedValue({ success: true }),
  downloadDocument: vi.fn().mockResolvedValue(new Blob(['mock data'])),
  processDocument: vi.fn().mockResolvedValue({ success: true, message: 'Processing started' }),
  reindexDocument: vi.fn().mockResolvedValue({ success: true, message: 'Reindexing queued' })
}));

// Mock Knowledge Graph API
vi.mock('../api/knowledgeGraph', () => ({
  listNodes: vi.fn().mockResolvedValue([
    { id: 'node-01', name: 'AegisAI Orchestrator', node_type: 'SystemComponent', confidence: 0.98, degree: 5, description: 'Core multi-agent coordination kernel.' },
    { id: 'node-02', name: 'Vector RAG Engine', node_type: 'Service', confidence: 0.92, degree: 4, description: 'Hybrid sparse-dense retrieval pipeline.' },
    { id: 'node-03', name: 'Memory Vault', node_type: 'Storage', confidence: 0.95, degree: 3, description: 'Multi-tier semantic and episodic memory.' }
  ]),
  listEdges: vi.fn().mockResolvedValue([
    { id: 'edge-01', source_node_id: 'node-01', target_node_id: 'node-02', relationship_type: 'ORCHESTRATES', confidence: 0.95, weight: 1.0 },
    { id: 'edge-02', source_node_id: 'node-01', target_node_id: 'node-03', relationship_type: 'PERSISTS_TO', confidence: 0.90, weight: 0.8 }
  ]),
  getNode: vi.fn().mockResolvedValue({
    id: 'node-01',
    name: 'AegisAI Orchestrator',
    node_type: 'SystemComponent',
    confidence: 0.98,
    degree: 5,
    description: 'Core multi-agent coordination kernel.'
  }),
  getNeighbors: vi.fn().mockResolvedValue({
    nodes: [
      { id: 'node-02', name: 'Vector RAG Engine', node_type: 'Service', confidence: 0.92 }
    ],
    edges: [
      { id: 'edge-01', source_node_id: 'node-01', target_node_id: 'node-02', relationship_type: 'ORCHESTRATES', confidence: 0.95 }
    ]
  }),
  getRelatedEntities: vi.fn().mockResolvedValue({
    related_entities: [
      { id: 'node-02', name: 'Vector RAG Engine', node_type: 'Service', confidence: 0.92 }
    ]
  }),
  searchEnhanced: vi.fn().mockResolvedValue({
    results: [
      { id: 'node-01', name: 'AegisAI Orchestrator', node_type: 'SystemComponent', score: 0.99 }
    ]
  }),
  findPath: vi.fn().mockResolvedValue({
    path_found: true,
    steps: [
      { from_node_name: 'AegisAI Orchestrator', to_node_name: 'Vector RAG Engine', relationship_type: 'ORCHESTRATES' }
    ],
    nodes: [
      { id: 'node-01', name: 'AegisAI Orchestrator' },
      { id: 'node-02', name: 'Vector RAG Engine' }
    ],
    distance: 1
  }),
  getGraphContext: vi.fn().mockResolvedValue({
    formatted_context: 'AegisAI Orchestrator coordinates the Vector RAG Engine and stores contextual memories in Memory Vault.',
    entities: [],
    relationships: []
  }),
  getDocumentEntities: vi.fn().mockResolvedValue([
    { id: 'node-01', name: 'AegisAI Orchestrator', node_type: 'SystemComponent', confidence: 0.98 }
  ]),
  getDocumentRelationships: vi.fn().mockResolvedValue([
    { id: 'edge-01', source_node_id: 'node-01', target_node_id: 'node-02', relationship_type: 'ORCHESTRATES', confidence: 0.95 }
  ]),
  extractDocumentGraph: vi.fn().mockResolvedValue({
    extracted_entities: 4,
    extracted_relations: 3
  }),
  rebuildDocumentGraph: vi.fn().mockResolvedValue({ success: true }),
  syncGraphNodeToMemory: vi.fn().mockResolvedValue({ success: true, memory_id: 'mem-999' }),
  getGraphAnalyticsOverview: vi.fn().mockResolvedValue({
    total_nodes: 3,
    total_edges: 2,
    density: 0.33,
    avg_degree: 1.33,
    connected_components: 1,
    avg_confidence: 0.95
  }),
  getGraphHealth: vi.fn().mockResolvedValue({
    status: 'healthy',
    isolated_nodes: 0,
    duplicate_candidates: 0,
    low_confidence_edges: 0
  }),
  getTopConnectedEntities: vi.fn().mockResolvedValue({
    top_entities: [
      { id: 'node-01', name: 'AegisAI Orchestrator', degree: 5 }
    ]
  }),
  getOrphanNodes: vi.fn().mockResolvedValue({ orphan_nodes: [] }),
  getDuplicateCandidates: vi.fn().mockResolvedValue({ duplicates: [] }),
  reasonGraph: vi.fn().mockResolvedValue({
    graph_context: 'The multi-agent system uses orchestrator routing to dispatch hybrid retrieval requests.',
    matched_nodes_count: 3,
    confidence: 0.96
  })
}));

// Mock RAG API
vi.mock('../api/rag', () => ({
  queryRAG: vi.fn().mockResolvedValue({
    query: 'How does AegisAI execute multi-agent coordination?',
    answer: 'AegisAI utilizes an autonomous multi-agent orchestration architecture with dynamic subagent routing [1].',
    citations: [
      {
        citation_number: 1,
        document_id: 'doc-001',
        document_title: 'architecture_specification_v2.pdf',
        chunk_id: 'chk-001',
        snippet: 'AegisAI utilizes an autonomous multi-agent orchestration architecture with dynamic subagent routing and sandboxed tool execution.',
        similarity: 0.94
      }
    ],
    processing_time_ms: 142
  }),
  queryHybridRAG: vi.fn().mockResolvedValue({
    query: 'How does AegisAI execute multi-agent coordination?',
    answer: 'AegisAI combines dense embeddings and BM25 sparse scoring to retrieve relevant chunks [1].',
    citations: [
      {
        citation_number: 1,
        document_id: 'doc-001',
        document_title: 'architecture_specification_v2.pdf',
        chunk_id: 'chk-001',
        snippet: 'AegisAI combines dense embeddings and BM25 sparse scoring.',
        similarity: 0.96
      }
    ],
    processing_time_ms: 168
  }),
  getRAGQueries: vi.fn().mockResolvedValue([
    {
      id: 'rag-q-01',
      query: 'How does AegisAI execute multi-agent coordination?',
      created_at: '2026-10-05T11:00:00Z',
      citations_count: 1
    }
  ])
}));

const mockAuthUser = {
  id: 'user-01',
  name: 'Test Administrator',
  email: 'admin@aegisai.enterprise',
  role: 'admin'
};

const renderWithProviders = (ui) => {
  return render(
    <ThemeProvider>
      <AuthContext.Provider value={{ user: mockAuthUser, isAuthenticated: true }}>
        <ToastProvider>
          {ui}
        </ToastProvider>
      </AuthContext.Provider>
    </ThemeProvider>
  );
};

describe('Phase 12.8 — Knowledge Intelligence Center Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('UserDocuments / Knowledge Center', () => {
    it('renders Knowledge Intelligence header and KPI summary strip', async () => {
      renderWithProviders(<UserDocuments />);

      expect(screen.getByText(/Knowledge Intelligence Center/i)).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText(/Total Documents/i)).toBeInTheDocument();
        expect(screen.getByText(/Indexed & Ready/i)).toBeInTheDocument();
        expect(screen.getByText(/Processing Pipeline/i)).toBeInTheDocument();
        expect(screen.getByText(/Indexed Chunks/i)).toBeInTheDocument();
      });
    });

    it('renders document table with document items and metadata', async () => {
      renderWithProviders(<UserDocuments />);

      await waitFor(() => {
        expect(screen.getAllByText('architecture_specification_v2.pdf').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('security_compliance_soc2.docx')).toBeInTheDocument();
      });
    });

    it('opens upload document modal when clicking upload button', async () => {
      renderWithProviders(<UserDocuments />);

      const uploadBtns = screen.getAllByRole('button', { name: /Upload Document/i });
      fireEvent.click(uploadBtns[0]);

      await waitFor(() => {
        expect(screen.getByText(/Upload Workspace Document/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Browse Files/i })).toBeInTheDocument();
      });
    });

    it('allows switching to Knowledge & RAG Search tab and running a query', async () => {
      renderWithProviders(<UserDocuments />);

      const ragTab = screen.getByRole('button', { name: /Knowledge & RAG Search/i });
      fireEvent.click(ragTab);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Ask a question across your workspace documents/i)).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Ask a question across your workspace documents/i);
      fireEvent.change(searchInput, { target: { value: 'How does AegisAI execute multi-agent coordination?' } });

      const executeBtn = screen.getByRole('button', { name: /Query Knowledge/i });
      fireEvent.click(executeBtn);

      await waitFor(() => {
        expect(screen.getByText(/Synthesized Grounded Answer/i)).toBeInTheDocument();
        expect(screen.getByText(/Supporting Citations/i)).toBeInTheDocument();
      });
    });

    it('opens Evidence Drawer when clicking Supporting Citation', async () => {
      renderWithProviders(<UserDocuments />);

      const ragTab = screen.getByRole('button', { name: /Knowledge & RAG Search/i });
      fireEvent.click(ragTab);

      const searchInput = screen.getByPlaceholderText(/Ask a question across your workspace documents/i);
      fireEvent.change(searchInput, { target: { value: 'How does AegisAI execute multi-agent coordination?' } });

      const executeBtn = screen.getByRole('button', { name: /Query Knowledge/i });
      fireEvent.click(executeBtn);

      await waitFor(() => {
        expect(screen.getByText(/Synthesized Grounded Answer/i)).toBeInTheDocument();
      });

      const citationBtn = screen.getByRole('button', { name: /\[1\] architecture_specification_v2\.pdf/i });
      fireEvent.click(citationBtn);

      await waitFor(() => {
        expect(screen.getByText(/Evidence Grounding Inspector/i)).toBeInTheDocument();
      });
    });
  });

  describe('UserGraph / Knowledge Graph Explorer', () => {
    it('renders Knowledge Graph header and KPI metrics strip', async () => {
      renderWithProviders(<UserGraph />);

      expect(screen.getByText(/Knowledge Graph Explorer/i)).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText(/Total Entities/i)).toBeInTheDocument();
        expect(screen.getByText(/Relationships/i)).toBeInTheDocument();
        expect(screen.getByText(/Average Confidence/i)).toBeInTheDocument();
        expect(screen.getByText(/Graph Density/i)).toBeInTheDocument();
      });
    });

    it('renders entity nodes in the canvas', async () => {
      renderWithProviders(<UserGraph />);

      await waitFor(() => {
        expect(screen.getByLabelText('AegisAI Orchestrator')).toBeInTheDocument();
        expect(screen.getByLabelText('Vector RAG Engine')).toBeInTheDocument();
      });
    });

    it('opens Node Inspector drawer when clicking an entity item', async () => {
      renderWithProviders(<UserGraph />);

      await waitFor(() => {
        expect(screen.getByLabelText('AegisAI Orchestrator')).toBeInTheDocument();
      });

      const nodeButton = screen.getByLabelText('AegisAI Orchestrator');
      fireEvent.click(nodeButton);

      await waitFor(() => {
        expect(screen.getByText(/Core multi-agent coordination kernel/i)).toBeInTheDocument();
      });
    });

    it('opens Graph Pathfinder modal', async () => {
      renderWithProviders(<UserGraph />);

      const pathfinderBtn = screen.getByRole('button', { name: /Pathfinder/i });
      fireEvent.click(pathfinderBtn);

      await waitFor(() => {
        expect(screen.getByText(/Graph Pathfinder/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Find Path/i })).toBeInTheDocument();
      });
    });

    it('opens Graph Analytics & Health modal', async () => {
      renderWithProviders(<UserGraph />);

      const analyticsBtn = screen.getByRole('button', { name: /Analytics & Health/i });
      fireEvent.click(analyticsBtn);

      await waitFor(() => {
        expect(screen.getByText(/Knowledge Graph Analytics & Health/i)).toBeInTheDocument();
        expect(screen.getByText(/Diagnostic Status/i)).toBeInTheDocument();
      });
    });

    it('opens Subgraph Reasoning modal', async () => {
      renderWithProviders(<UserGraph />);

      const reasonBtn = screen.getByRole('button', { name: /Graph Reasoning/i });
      fireEvent.click(reasonBtn);

      await waitFor(() => {
        expect(screen.getByText(/Multi-Agent Graph Reasoning/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Execute Reasoning/i })).toBeInTheDocument();
      });
    });

    it('opens Plain-Text Accessible Representation modal', async () => {
      renderWithProviders(<UserGraph />);

      const accessibleBtn = screen.getByRole('button', { name: /Accessible Outline/i });
      fireEvent.click(accessibleBtn);

      await waitFor(() => {
        expect(screen.getByText(/Accessible Knowledge Graph Outline/i)).toBeInTheDocument();
      });
    });
  });
});
