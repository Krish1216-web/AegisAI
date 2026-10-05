import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BrainCircuit,
  Bot,
  Search,
  Cpu,
  Layers,
  Activity,
  ShieldCheck,
  ShieldAlert,
  Database,
  FileText,
  Server,
  Workflow,
  GitBranch,
  CheckCircle2,
  RefreshCw,
  ArrowRight,
  ArrowUpRight,
  Sliders,
  ChevronRight,
  Info,
  ExternalLink,
  Eye,
  Columns,
  Sparkles,
  Lock,
  Zap,
  Check
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import {
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  MetricCard,
  EmptyState,
  Skeleton,
  Drawer,
  Tabs,
  CodeBlock
} from '../../components/ui';
import { getPlatformCapabilities, getPlatformStatus } from '../../api/platform';

export default function UserAiMarket({ triggerNotification }) {
  const navigate = useNavigate();
  const { user, role, workspaceId } = useAuth();
  const { theme } = useTheme();

  // Navigation / View State
  const [viewMode, setViewMode] = useState('directory'); // directory | architecture | compare
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all'); // all | coordination | knowledge | execution | verification
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Comparison State
  const [compareAgent1Id, setCompareAgent1Id] = useState('orchestrator');
  const [compareAgent2Id, setCompareAgent2Id] = useState('planner');

  // Platform Telemetry State
  const [platformStatus, setPlatformStatus] = useState(null);
  const [registeredCapabilities, setRegisteredCapabilities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // 9 Canonical System Agents of the AegisAI Workforce
  const systemAgents = useMemo(() => [
    {
      id: 'orchestrator',
      name: 'Orchestrator Agent',
      code: 'SYSTEM_AGENT :: ORCHESTRATOR',
      category: 'coordination',
      type: 'System Agent',
      stage: '01 — Ingestion & Dispatch',
      status: 'AVAILABLE',
      role: 'Global Swarm Coordinator',
      purpose: 'Coordinates overall intelligence execution, enforces workspace boundaries, and dispatches sub-goals to specialized agents in deterministic DAG workflows.',
      capabilities: ['Pipeline Dispatch', 'DAG Synchronization', 'Boundary Enforcement', 'Telemetry Streaming'],
      connectedSubsystems: ['Platform Engine', 'Background Worker Queue', 'WebSocket Bus'],
      upstream: ['User / Ingress API'],
      downstream: ['Planner Agent', 'Response Generator'],
      governance: {
        scope: 'Workspace-Scoped',
        rbac: 'Any Authenticated Role',
        policy: 'Fail-Closed Routing',
        security: 'Recursive Secret Redaction, Non-Root UID 10001'
      },
      evidenceFormat: 'Correlation ID, Execution DAG Manifest, Subsystem Event Stream',
      icon: <BrainCircuit size={18} className="text-cyan-400" />
    },
    {
      id: 'planner',
      name: 'Planner Agent',
      code: 'SYSTEM_AGENT :: PLANNER',
      category: 'coordination',
      type: 'System Agent',
      stage: '02 — Task Decomposition',
      status: 'AVAILABLE',
      role: 'DAG Task Decomposition',
      purpose: 'Decomposes complex natural language goals into structured topological task nodes, resolving dependencies and required capability bindings.',
      capabilities: ['Goal Formulation', 'Topological Task Sorting', 'Capability Binding', 'Dependency Validation'],
      connectedSubsystems: ['Platform Capability Registry', 'Workflow Parser'],
      upstream: ['Orchestrator Agent'],
      downstream: ['Research Agent', 'RAG Agent', 'Memory Agent', 'Tool Executor'],
      governance: {
        scope: 'Workspace-Scoped',
        rbac: 'Member, Admin, Owner',
        policy: 'Deterministic DAG Generation',
        security: 'Schema Validation, Circular Dependency Guard'
      },
      evidenceFormat: 'Structured JSON Task Plan, Node Dependency List',
      icon: <Workflow size={18} className="text-purple-400" />
    },
    {
      id: 'research',
      name: 'Research Agent',
      code: 'SYSTEM_AGENT :: RESEARCH',
      category: 'knowledge',
      type: 'System Agent',
      stage: '03 — Information Gathering',
      status: 'AVAILABLE',
      role: 'Information Gathering & Web Synthesis',
      purpose: 'Gathers external technical information, crawls authorized web domains, and extracts verified external documentation.',
      capabilities: ['Semantic Web Search', 'API Documentation Extraction', 'Relevance Scoring', 'Evidence Tagging'],
      connectedSubsystems: ['Tavily Search Engine', 'External HTTP Client'],
      upstream: ['Planner Agent'],
      downstream: ['Critic & Consensus Agent', 'Response Generator'],
      governance: {
        scope: 'Outbound Filtered',
        rbac: 'Member, Admin, Owner',
        policy: 'SSRF Safe Egress',
        security: 'Private CIDR Block, Domain Whitelist'
      },
      evidenceFormat: 'Source URLs, Trust Scores, Crawl Timestamps',
      icon: <Search size={18} className="text-blue-400" />
    },
    {
      id: 'memory',
      name: 'Memory Agent',
      code: 'SYSTEM_AGENT :: MEMORY',
      category: 'knowledge',
      type: 'System Agent',
      stage: '03 — Context Retrieval',
      status: 'AVAILABLE',
      role: 'Cognitive Memory Vault Recall',
      purpose: 'Indexes conversational history, agent reflections, and entity profiles into semantic vector stores, enforcing strict tenant isolation.',
      capabilities: ['Episodic Memory Recall', 'Semantic Vector Search', 'Importance Scoring', 'Memory Decay Management'],
      connectedSubsystems: ['Qdrant Vector Database', 'Cognitive Memory Vault'],
      upstream: ['Planner Agent', 'Orchestrator Agent'],
      downstream: ['Critic & Consensus Agent', 'Response Generator'],
      governance: {
        scope: 'Strict Multi-Tenant Boundary',
        rbac: 'Member, Admin, Owner',
        policy: 'Mandatory Workspace Filter',
        security: 'Row-Level Tenant Isolation, Cosine Similarity Filtering'
      },
      evidenceFormat: 'Memory Vector IDs, Cosine Similarity Scores, Context Snippets',
      icon: <Database size={18} className="text-indigo-400" />
    },
    {
      id: 'rag',
      name: 'Enterprise RAG Agent',
      code: 'SYSTEM_AGENT :: RAG',
      category: 'knowledge',
      type: 'System Agent',
      stage: '03 — Document Intelligence',
      status: 'AVAILABLE',
      role: 'Enterprise Document Intelligence',
      purpose: 'Ingests documents (PDF, CSV, TXT, DOCX), computes 1536-dim embeddings, and retrieves relevant chunks with exact physical citations.',
      capabilities: ['Document Chunk Extraction', 'Hybrid Vector Retrieval', 'Citation Attribution', 'Chunk Deduplication'],
      connectedSubsystems: ['Document Processing Worker', 'PostgreSQL Vector Store'],
      upstream: ['Planner Agent'],
      downstream: ['Critic & Consensus Agent', 'Response Generator'],
      governance: {
        scope: 'Workspace-Scoped',
        rbac: 'Member, Admin, Owner',
        policy: 'Physical Document Reconciliation',
        security: 'Anti-Tamper Hash Verification, Workspace Filtering'
      },
      evidenceFormat: 'Document IDs, Page Numbers, Chunk Offsets, Exact Text Spans',
      icon: <FileText size={18} className="text-teal-400" />
    },
    {
      id: 'graph',
      name: 'Graph Reasoning Agent',
      code: 'SYSTEM_AGENT :: GRAPH_REASONING',
      category: 'knowledge',
      type: 'System Agent',
      stage: '03 — Relationship Traversal',
      status: 'AVAILABLE',
      role: 'Knowledge Graph Synthesis',
      purpose: 'Traverses multi-hop entity relationships and semantic triples to answer structured enterprise graph queries.',
      capabilities: ['Multi-Hop Traversal', 'Entity Extraction', 'Relationship Inference', 'Graph Context Assembly'],
      connectedSubsystems: ['Knowledge Graph Store', 'Entity Resolution Engine'],
      upstream: ['Planner Agent'],
      downstream: ['Critic & Consensus Agent', 'Response Generator'],
      governance: {
        scope: 'Workspace-Scoped',
        rbac: 'Member, Admin, Owner',
        policy: 'Graph Traversal Depth Limit (max 4 hops)',
        security: 'Circular Path Detection, Tenant Boundary Assertion'
      },
      evidenceFormat: 'Entity Nodes, Relationship Edge IDs, Path Traversal Sequence',
      icon: <GitBranch size={18} className="text-emerald-400" />
    },
    {
      id: 'executor',
      name: 'Tool Executor Agent',
      code: 'SYSTEM_AGENT :: TOOL_EXECUTOR',
      category: 'execution',
      type: 'System Agent',
      stage: '04 — Sandboxed Execution',
      status: 'AVAILABLE',
      role: 'Sandboxed MCP & Tool Execution',
      purpose: 'Invokes external tools, APIs, and cloud resources via standardized Model Context Protocol (MCP) server daemons.',
      capabilities: ['MCP Tool Invocation', 'Resource Extraction', 'Parameter Validation', 'Execution Normalization'],
      connectedSubsystems: ['Model Context Protocol (MCP) Daemons', 'Sandboxed Docker Workers'],
      upstream: ['Planner Agent'],
      downstream: ['Critic & Consensus Agent'],
      governance: {
        scope: 'Permission Gated',
        rbac: 'Admin, Owner (Member with confirmation)',
        policy: 'Human-in-the-loop Approval Gates',
        security: 'Output Sanitization, Recursive Secret Redaction'
      },
      evidenceFormat: 'Tool Execution Tokens, Sanitized Stdout, Audit Event Signatures',
      icon: <Server size={18} className="text-amber-400" />
    },
    {
      id: 'critic',
      name: 'Critic & Consensus Agent',
      code: 'SYSTEM_AGENT :: CRITIC',
      category: 'verification',
      type: 'System Agent',
      stage: '05 — Quality & Safety Gate',
      status: 'AVAILABLE',
      role: 'Verification & Quality Gate',
      purpose: 'Evaluates candidate agent outputs against ground truth evidence, calculates factuality confidence, and detects contradictions.',
      capabilities: ['Factuality Evaluation', 'Hallucination Detection', 'Citation Reconciliation', 'Consensus Voting'],
      connectedSubsystems: ['Confidence Scorer', 'Verification Engine'],
      upstream: ['Research Agent', 'Memory Agent', 'RAG Agent', 'Graph Agent', 'Tool Executor'],
      downstream: ['Response Generator'],
      governance: {
        scope: 'Fail-Closed Gate',
        rbac: 'System Automated',
        policy: 'Strict Consensus Threshold (>= 0.70)',
        security: 'Prompt Injection Neutralizer, Anti-Hallucination Gate'
      },
      evidenceFormat: 'Confidence Score (0.00-1.00), Decision Record, Contradiction Flags',
      icon: <ShieldCheck size={18} className="text-rose-400" />
    },
    {
      id: 'response',
      name: 'Response Generator',
      code: 'SYSTEM_AGENT :: RESPONSE_GENERATOR',
      category: 'verification',
      type: 'System Agent',
      stage: '06 — Evidence-Backed Synthesis',
      status: 'AVAILABLE',
      role: 'Evidence-Backed Synthesis',
      purpose: 'Synthesizes verified evidence into clean, markdown-formatted responses with explicit citations and SHA-256 audit chaining.',
      capabilities: ['Output Formatting', 'Citation Embedding', 'Cryptographic Sealing', 'Delivery Normalization'],
      connectedSubsystems: ['Audit Ledger', 'WebSocket Delivery Channel'],
      upstream: ['Critic & Consensus Agent'],
      downstream: ['User / Ingress Response'],
      governance: {
        scope: 'Workspace-Scoped',
        rbac: 'Any Authenticated Role',
        policy: 'Truth-in-Output Guarantee',
        security: 'SHA-256 Hash Chaining, Zero Credential Exposure'
      },
      evidenceFormat: 'Final Provenance Chain, Cryptographic Signature, Delivery Timestamp',
      icon: <Sparkles size={18} className="text-emerald-400" />
    }
  ], []);

  // Fetch registered platform capability telemetry
  const fetchTelemetry = useCallback(async () => {
    setLoadError(null);
    try {
      const [statusRes, capsRes] = await Promise.allSettled([
        getPlatformStatus(),
        getPlatformCapabilities('agent')
      ]);

      if (statusRes.status === 'fulfilled') setPlatformStatus(statusRes.value);
      if (capsRes.status === 'fulfilled') setRegisteredCapabilities(capsRes.value?.items || []);
    } catch (err) {
      console.error('Failed to load agent telemetry:', err);
      setLoadError('Failed to synchronize live agent capabilities.');
    } finally {
      setIsLoading(false);
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    fetchTelemetry();
  }, [fetchTelemetry]);

  const handleSync = () => {
    setIsSyncing(true);
    fetchTelemetry();
  };

  const handleOpenInspector = (agent) => {
    setSelectedAgent(agent);
    setIsDrawerOpen(true);
  };

  // Filtered Agent List
  const filteredAgents = useMemo(() => {
    return systemAgents.filter((agent) => {
      const matchesSearch =
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.purpose.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.capabilities.some((c) => c.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesCategory =
        categoryFilter === 'all' || agent.category === categoryFilter;

      return matchesSearch && matchesCategory;
    });
  }, [systemAgents, searchQuery, categoryFilter]);

  // Comparison Agents
  const agent1 = systemAgents.find((a) => a.id === compareAgent1Id) || systemAgents[0];
  const agent2 = systemAgents.find((a) => a.id === compareAgent2Id) || systemAgents[1];

  return (
    <div className="flex flex-col gap-8 animate-fade-in font-sans text-slate-100 pb-12">
      
      {/* ==============================================================================
       * 1. Header & Workforce Control Surface
       * ============================================================================== */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-white uppercase flex items-center gap-2.5">
              <Bot size={22} className="text-cyan-400" />
              Agent Center — AI Workforce Control
            </h1>
            <Badge variant="cyan" size="sm">
              SYSTEM WORKFORCE
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1.5">
            Observe, understand, and govern the 9 autonomous system agents powering AegisAI's orchestration pipeline.
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2.5">
          {/* View Mode Toggle */}
          <div className="flex rounded-lg border border-white/10 bg-[#0d1017] p-0.5 text-xs">
            <button
              onClick={() => setViewMode('directory')}
              className={`px-3 py-1.5 rounded-md font-mono text-xs transition-all cursor-pointer ${
                viewMode === 'directory'
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Directory
            </button>
            <button
              onClick={() => setViewMode('architecture')}
              className={`px-3 py-1.5 rounded-md font-mono text-xs transition-all cursor-pointer ${
                viewMode === 'architecture'
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Architecture Map
            </button>
            <button
              onClick={() => setViewMode('compare')}
              className={`px-3 py-1.5 rounded-md font-mono text-xs transition-all cursor-pointer ${
                viewMode === 'compare'
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Comparison
            </button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleSync}
            isLoading={isSyncing}
            leftIcon={<RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} />}
          >
            Sync
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/user/chat')}
            leftIcon={<Sparkles size={14} />}
          >
            Use in Workspace
          </Button>
        </div>
      </div>

      {/* Global Load Error Banner */}
      {loadError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} className="shrink-0" />
            <span>{loadError}</span>
          </div>
          <Button variant="ghost" size="xs" onClick={fetchTelemetry}>
            Retry
          </Button>
        </div>
      )}

      {/* ==============================================================================
       * 2. Workforce Overview KPI Strip
       * ============================================================================== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="System Workforce"
          value="9 Active Agents"
          description="Deterministic multi-agent collective"
          icon={<Bot size={18} className="text-cyan-400" />}
          className="border-white/[0.08] bg-[#0d1017]/80"
        />
        <MetricCard
          title="Swarm Topology"
          value="DAG Sequential & Parallel"
          description="Dependency-resolved task graph"
          icon={<Workflow size={18} className="text-purple-400" />}
          className="border-white/[0.08] bg-[#0d1017]/80"
        />
        <MetricCard
          title="Verification Gate"
          value="Consensus Critic"
          description="Anti-hallucination factuality filter"
          icon={<ShieldCheck size={18} className="text-emerald-400" />}
          className="border-white/[0.08] bg-[#0d1017]/80"
        />
        <MetricCard
          title="Security Boundary"
          value="Fail-Closed Isolation"
          description="Workspace tenant boundaries enforced"
          icon={<Lock size={18} className="text-amber-400" />}
          className="border-white/[0.08] bg-[#0d1017]/80"
        />
      </div>

      {/* ==============================================================================
       * 3. DIRECTORY VIEW
       * ============================================================================== */}
      {viewMode === 'directory' && (
        <div className="flex flex-col gap-6">
          
          {/* Search & Category Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search agents by name, role, capability (e.g. Planning)..."
                className="w-full rounded-xl border border-white/10 bg-[#0d1017]/80 py-2 pl-9 pr-4 text-xs text-white placeholder:text-slate-500 outline-none focus:border-cyan-500/50 transition-all font-sans"
              />
            </div>

            {/* Category Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {[
                { id: 'all', label: 'All Agents' },
                { id: 'coordination', label: 'Coordination' },
                { id: 'knowledge', label: 'Knowledge & Memory' },
                { id: 'execution', label: 'Execution & Tools' },
                { id: 'verification', label: 'Verification' }
              ].map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setCategoryFilter(cat.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all shrink-0 cursor-pointer ${
                    categoryFilter === cat.id
                      ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                      : 'bg-white/[0.02] border border-white/5 text-slate-400 hover:text-white'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Agent Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredAgents.length > 0 ? (
              filteredAgents.map((agent) => (
                <Card
                  key={agent.id}
                  className="border-white/[0.08] bg-[#0d1017]/80 hover:border-cyan-500/30 transition-all flex flex-col justify-between"
                >
                  <CardHeader className="border-b border-white/[0.06] pb-3.5">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-white/5 border border-white/5">{agent.icon}</div>
                        <div>
                          <h3 className="text-sm font-bold text-white">{agent.name}</h3>
                          <span className="text-[10px] font-mono text-cyan-400">{agent.role}</span>
                        </div>
                      </div>
                      <StatusBadge status={agent.status} size="xs" />
                    </div>
                  </CardHeader>

                  <CardContent className="p-4 flex flex-col gap-3 flex-1">
                    <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider block">
                      {agent.stage}
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">
                      {agent.purpose}
                    </p>

                    {/* Capabilities Tags */}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {agent.capabilities.map((cap) => (
                        <span
                          key={cap}
                          className="px-2 py-0.5 rounded bg-white/[0.03] border border-white/5 text-[10px] font-mono text-slate-400"
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                  </CardContent>

                  <CardFooter className="border-t border-white/[0.06] p-4 flex items-center justify-between gap-2">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleOpenInspector(agent)}
                      leftIcon={<Eye size={12} />}
                    >
                      Inspect Agent
                    </Button>
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={() => navigate('/user/chat')}
                      rightIcon={<ArrowRight size={12} />}
                    >
                      Use in Workspace
                    </Button>
                  </CardFooter>
                </Card>
              ))
            ) : (
              <div className="col-span-full">
                <EmptyState
                  icon={<Bot size={24} />}
                  title="No matching agents found"
                  description="Try adjusting your search query or switching the category filter."
                  actionLabel="Clear Filters"
                  onAction={() => {
                    setSearchQuery('');
                    setCategoryFilter('all');
                  }}
                />
              </div>
            )}
          </div>

        </div>
      )}

      {/* ==============================================================================
       * 4. ARCHITECTURE MAP VIEW
       * ============================================================================== */}
      {viewMode === 'architecture' && (
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Workflow size={16} className="text-cyan-400" />
                Multi-Agent Collective Architecture & Flow
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                End-to-end task decomposition, retrieval, execution, consensus verification, and response synthesis sequence.
              </CardDescription>
            </div>
            <Badge variant="cyan" size="xs">TOPOLOGICAL DAG</Badge>
          </CardHeader>

          <CardContent className="p-6 flex flex-col gap-8">
            {/* Visual Pipeline Flow Sequence */}
            <div className="p-6 rounded-2xl border border-cyan-500/20 bg-cyan-500/[0.02] flex flex-col gap-6">
              
              {/* Level 1: Ingress & Coordination */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <div className="p-3.5 rounded-xl border border-white/10 bg-[#07090e] text-center min-w-[200px]">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold block">01. COORDINATION</span>
                  <h4 className="text-xs font-bold text-white mt-1">Orchestrator Agent</h4>
                  <span className="text-[10px] text-slate-400">Receives & validates user request</span>
                </div>

                <ChevronRight size={18} className="text-slate-600 rotate-90 sm:rotate-0" />

                <div className="p-3.5 rounded-xl border border-white/10 bg-[#07090e] text-center min-w-[200px]">
                  <span className="text-[10px] font-mono text-purple-400 uppercase font-bold block">02. PLANNING</span>
                  <h4 className="text-xs font-bold text-white mt-1">Planner Agent</h4>
                  <span className="text-[10px] text-slate-400">Decomposes DAG sub-goals</span>
                </div>
              </div>

              {/* Connector Down */}
              <div className="flex justify-center text-slate-600">
                <ChevronRight size={18} className="rotate-90" />
              </div>

              {/* Level 2: Specialized Parallel Workers */}
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                {[
                  { name: 'Research Agent', desc: 'Web & Spec Crawl', color: 'text-blue-400' },
                  { name: 'Memory Agent', desc: 'Episodic Recall', color: 'text-indigo-400' },
                  { name: 'RAG Agent', desc: 'Document Vectors', color: 'text-teal-400' },
                  { name: 'Graph Agent', desc: 'Entity Triples', color: 'text-emerald-400' },
                  { name: 'Tool Executor', desc: 'MCP Tool Calls', color: 'text-amber-400' },
                ].map((spec) => (
                  <div key={spec.name} className="p-3 rounded-xl border border-white/10 bg-[#07090e] text-center">
                    <span className={`text-[10px] font-mono uppercase font-bold block ${spec.color}`}>PARALLEL NODE</span>
                    <h5 className="text-xs font-bold text-white mt-1">{spec.name}</h5>
                    <span className="text-[10px] text-slate-400 block mt-0.5">{spec.desc}</span>
                  </div>
                ))}
              </div>

              {/* Connector Down */}
              <div className="flex justify-center text-slate-600">
                <ChevronRight size={18} className="rotate-90" />
              </div>

              {/* Level 3: Verification & Response */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <div className="p-3.5 rounded-xl border border-rose-500/30 bg-[#07090e] text-center min-w-[200px]">
                  <span className="text-[10px] font-mono text-rose-400 uppercase font-bold block">05. QUALITY GATE</span>
                  <h4 className="text-xs font-bold text-white mt-1">Critic & Consensus Agent</h4>
                  <span className="text-[10px] text-slate-400">Verifies evidence & factuality</span>
                </div>

                <ChevronRight size={18} className="text-slate-600 rotate-90 sm:rotate-0" />

                <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-[#07090e] text-center min-w-[200px]">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold block">06. DELIVERY</span>
                  <h4 className="text-xs font-bold text-white mt-1">Response Generator</h4>
                  <span className="text-[10px] text-slate-400">Evidence-backed response</span>
                </div>
              </div>

            </div>

            {/* Accessible Text Fallback for Screen Readers and Plain Text Inspection */}
            <div className="border-t border-white/[0.08] pt-6">
              <span className="text-xs font-mono uppercase text-slate-400 font-bold block mb-3">
                Accessible Architectural Sequence & Handshake Protocol:
              </span>
              <ol className="list-decimal list-inside text-xs text-slate-300 space-y-2 leading-relaxed font-mono">
                <li><strong className="text-cyan-400">Orchestrator Agent:</strong> Intercepts natural language request, establishes workspace isolation boundaries, and logs correlation metadata.</li>
                <li><strong className="text-purple-400">Planner Agent:</strong> Generates a directed acyclic graph (DAG) of verified tasks, attaching capability requirements.</li>
                <li><strong className="text-blue-400">Specialized Swarm Agents:</strong> Research, Memory, RAG, Graph Reasoning, and Tool Executor execute sub-tasks concurrently.</li>
                <li><strong className="text-rose-400">Critic & Consensus Agent:</strong> Validates outputs, verifies citations, checks consensus, and filters hallucinations.</li>
                <li><strong className="text-emerald-400">Response Generator:</strong> Packages verified findings with citation references and applies SHA-256 cryptographic audit sealing.</li>
              </ol>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ==============================================================================
       * 5. AGENT COMPARISON VIEW
       * ============================================================================== */}
      {viewMode === 'compare' && (
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Columns size={16} className="text-cyan-400" />
                Side-by-Side Agent Comparison
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Compare roles, capabilities, knowledge access, and governance controls across any two system agents.
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="p-6 flex flex-col gap-6">
            
            {/* Agent Selectors */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-mono text-slate-400 uppercase font-bold block mb-2">Select First Agent:</label>
                <select
                  value={compareAgent1Id}
                  onChange={(e) => setCompareAgent1Id(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#07090e] p-2.5 text-xs text-white outline-none focus:border-cyan-500/50"
                >
                  {systemAgents.map((ag) => (
                    <option key={ag.id} value={ag.id} className="bg-[#0d1017] text-white">
                      {ag.name} ({ag.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400 uppercase font-bold block mb-2">Select Second Agent:</label>
                <select
                  value={compareAgent2Id}
                  onChange={(e) => setCompareAgent2Id(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#07090e] p-2.5 text-xs text-white outline-none focus:border-cyan-500/50"
                >
                  {systemAgents.map((ag) => (
                    <option key={ag.id} value={ag.id} className="bg-[#0d1017] text-white">
                      {ag.name} ({ag.role})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Comparison Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-4">
              {[agent1, agent2].map((ag, idx) => (
                <div key={ag.id + idx} className="p-5 rounded-xl border border-white/10 bg-[#07090e]/60 flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-white/5 border border-white/5">{ag.icon}</div>
                      <div>
                        <h4 className="text-sm font-bold text-white">{ag.name}</h4>
                        <span className="text-[10px] font-mono text-cyan-400">{ag.role}</span>
                      </div>
                    </div>
                    <StatusBadge status={ag.status} size="xs" />
                  </div>

                  <div className="flex flex-col gap-3 text-xs">
                    <div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1">Purpose</span>
                      <p className="text-slate-300 leading-relaxed">{ag.purpose}</p>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1">Capabilities</span>
                      <div className="flex flex-wrap gap-1">
                        {ag.capabilities.map((c) => (
                          <span key={c} className="px-2 py-0.5 rounded bg-white/5 text-[10px] font-mono text-slate-300 border border-white/5">
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1">Connected Subsystems</span>
                      <p className="text-slate-400 font-mono text-[11px]">{ag.connectedSubsystems.join(', ')}</p>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1">Governance & Safety</span>
                      <div className="space-y-1 text-[11px] text-slate-400">
                        <div>Scope: <strong className="text-slate-200">{ag.governance.scope}</strong></div>
                        <div>RBAC: <strong className="text-slate-200">{ag.governance.rbac}</strong></div>
                        <div>Policy: <strong className="text-slate-200">{ag.governance.policy}</strong></div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

          </CardContent>
        </Card>
      )}

      {/* ==============================================================================
       * 6. Slide-Over Agent Inspector Drawer
       * ============================================================================== */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedAgent?.name || 'Agent Inspector'}
        description={selectedAgent?.code || 'SYSTEM_AGENT'}
        size="lg"
      >
        {selectedAgent && (
          <div className="flex flex-col gap-6 text-xs text-slate-300 font-sans">
            
            {/* Identity & Status */}
            <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-white/5 border border-white/5">{selectedAgent.icon}</div>
                <div>
                  <h4 className="text-sm font-bold text-white">{selectedAgent.name}</h4>
                  <span className="text-[11px] text-cyan-400 font-mono">{selectedAgent.role}</span>
                </div>
              </div>
              <StatusBadge status={selectedAgent.status} size="sm" />
            </div>

            {/* Purpose & Responsibility */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                PRIMARY OPERATIONAL PURPOSE
              </span>
              <p className="text-xs text-slate-200 leading-relaxed p-3.5 rounded-xl bg-[#07090e] border border-white/5">
                {selectedAgent.purpose}
              </p>
            </div>

            {/* Architecture Flow Placement */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                ARCHITECTURE PIPELINE STAGE & HANDOFF
              </span>
              <div className="p-3.5 rounded-xl bg-[#07090e] border border-white/5 flex flex-col gap-2 font-mono text-[11px]">
                <div>Stage: <strong className="text-cyan-400">{selectedAgent.stage}</strong></div>
                <div>Upstream Invoker: <span className="text-slate-300">{selectedAgent.upstream.join(', ')}</span></div>
                <div>Downstream Handshake: <span className="text-slate-300">{selectedAgent.downstream.join(', ')}</span></div>
              </div>
            </div>

            {/* Capabilities List */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                REGISTERED CAPABILITY PERMISSIONS
              </span>
              <div className="flex flex-wrap gap-1.5">
                {selectedAgent.capabilities.map((c) => (
                  <span
                    key={c}
                    className="px-2.5 py-1 rounded-md bg-white/[0.04] border border-white/10 text-xs font-mono text-slate-200"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>

            {/* Connected Subsystems */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                CONNECTED INFRASTRUCTURE SUBSYSTEMS
              </span>
              <div className="p-3.5 rounded-xl bg-[#07090e] border border-white/5 space-y-1 font-mono text-[11px]">
                {selectedAgent.connectedSubsystems.map((sub) => (
                  <div key={sub} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="text-slate-300">{sub}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Governance & Fail-Closed Controls */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                ENTERPRISE GOVERNANCE & SECURITY CONTROLS
              </span>
              <div className="p-3.5 rounded-xl bg-[#07090e] border border-white/5 flex flex-col gap-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Workspace Boundary Scope:</span>
                  <strong className="text-slate-200 font-mono">{selectedAgent.governance.scope}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Required RBAC Role:</span>
                  <strong className="text-slate-200 font-mono">{selectedAgent.governance.rbac}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Safety Policy:</span>
                  <strong className="text-slate-200 font-mono">{selectedAgent.governance.policy}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Security Defenses:</span>
                  <strong className="text-emerald-400 font-mono">{selectedAgent.governance.security}</strong>
                </div>
              </div>
            </div>

            {/* Evidence & Provenance Output Format */}
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block mb-1.5">
                EVIDENCE & AUDIT TRAIL OUTPUT SPECIFICATION
              </span>
              <div className="p-3.5 rounded-xl bg-[#07090e] border border-white/5 text-[11px] font-mono text-slate-400">
                {selectedAgent.evidenceFormat}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between gap-3">
              <Button variant="ghost" size="sm" onClick={() => setIsDrawerOpen(false)}>
                Close Inspector
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsDrawerOpen(false);
                  navigate('/user/chat');
                }}
                rightIcon={<ArrowRight size={14} />}
              >
                Launch in Workspace
              </Button>
            </div>

          </div>
        )}
      </Drawer>

    </div>
  );
}
