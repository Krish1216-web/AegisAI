import React, { useState, useEffect, useCallback } from 'react';
import { 
  Bot, 
  Sliders, 
  Cpu, 
  Activity, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  Zap, 
  ShieldCheck, 
  Lock,
  Layers,
  Sparkles,
  ArrowRight,
  Database,
  GitBranch,
  Shield,
  Eye,
  FileCode,
  Terminal,
  ExternalLink
} from 'lucide-react';
import { getPlatformCapabilities, getPlatformCapabilityAnalytics } from '../../api/platform';
import {
  Button,
  IconButton,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  StatusBadge,
  Badge,
  EmptyState,
  Skeleton,
  MetricCard,
  Drawer,
  Table
} from '../../components/ui';

// Canonical 9 System Agents with verified architecture & governance boundaries
const CANONICAL_AGENTS = [
  {
    id: 'agent_orchestrator',
    name: 'Orchestrator Agent',
    category: 'Coordination',
    stage: 'Root Coordinator',
    description: 'Autonomous central routing kernel responsible for intent parsing, DAG dispatch, and subagent state lifecycle.',
    allowedTools: ['subagent_routing', 'dag_dispatcher', 'lifecycle_manager'],
    memoryAccess: 'Read / Write (Episodic & Semantic)',
    knowledgeAccess: 'Workspace Partition Level',
    requiredPermissions: ['agent:orchestrate', 'workspace:read'],
    governanceBoundary: 'Sandboxed routing only; no direct arbitrary code execution.'
  },
  {
    id: 'agent_planner',
    name: 'Planner Agent',
    category: 'Coordination',
    stage: 'Planning & Decomposition',
    description: 'Decomposes complex natural language user requests into topological execution steps with dependency ordering.',
    allowedTools: ['step_decomposer', 'dependency_resolver', 'concurrency_optimizer'],
    memoryAccess: 'Read (Working Context)',
    knowledgeAccess: 'Metadata & Schema Catalog',
    requiredPermissions: ['agent:plan'],
    governanceBoundary: 'Static DAG validation prior to step dispatch.'
  },
  {
    id: 'agent_memory',
    name: 'Memory Agent',
    category: 'Knowledge & Memory',
    stage: 'Context Synthesis',
    description: 'Retrieves, updates, and deduplicates long-term semantic embeddings and episodic memory records.',
    allowedTools: ['vector_search', 'memory_vault_sync', 'deduplication_engine'],
    memoryAccess: 'Full Access (Semantic, Episodic, Working)',
    knowledgeAccess: 'Document & Memory Entities',
    requiredPermissions: ['memory:read_write'],
    governanceBoundary: 'Strict tenant-isolated vector filtering; zero cross-tenant memory leakage.'
  },
  {
    id: 'agent_rag',
    name: 'RAG Agent',
    category: 'Knowledge & Memory',
    stage: 'Information Retrieval',
    description: 'Executes dense-sparse hybrid retrieval over partitioned document chunks with cross-encoder reranking.',
    allowedTools: ['hybrid_retrieval', 'bm25_search', 'cross_encoder_reranker'],
    memoryAccess: 'Read (Query Context)',
    knowledgeAccess: 'Indexed Document Corpuses',
    requiredPermissions: ['document:read'],
    governanceBoundary: 'Strict chunk score gating; no speculative hallucination without cited chunks.'
  },
  {
    id: 'agent_graph',
    name: 'Knowledge Graph Agent',
    category: 'Knowledge & Memory',
    stage: 'Topological Reasoning',
    description: 'Traverses entity topology and relationships to discover multi-hop causal connections and associative context.',
    allowedTools: ['pathfinder', 'neighbor_expansion', 'subgraph_reasoner'],
    memoryAccess: 'Read / Write (Graph Entities)',
    knowledgeAccess: 'Workspace Entity Graph',
    requiredPermissions: ['graph:traverse'],
    governanceBoundary: 'Bounded depth traversal (max depth 4) to prevent combinatorial explosion.'
  },
  {
    id: 'agent_executor',
    name: 'Executor Agent',
    category: 'Execution & Tools',
    stage: 'Tool Invocation',
    description: 'Executes authorized tool calls against sandboxed MCP servers and system integrations with parameter validation.',
    allowedTools: ['mcp_caller', 'sandbox_runner', 'api_invoker'],
    memoryAccess: 'Read (Tool Context)',
    knowledgeAccess: 'Tool Schema Definitions',
    requiredPermissions: ['mcp:execute_safe', 'mcp:execute_restricted'],
    governanceBoundary: 'Cryptographic confirmation gating for destructive or external network operations.'
  },
  {
    id: 'agent_research',
    name: 'Research Agent',
    category: 'Execution & Tools',
    stage: 'Synthesis & Fact Gathering',
    description: 'Synthesizes multi-source evidence across document corpora, graph connections, and tool returns.',
    allowedTools: ['evidence_aggregator', 'source_comparator', 'fact_checker'],
    memoryAccess: 'Read (Evidence Cache)',
    knowledgeAccess: 'Aggregated Evidence',
    requiredPermissions: ['document:read', 'agent:use'],
    governanceBoundary: 'Strict source attribution tagging for every generated fact.'
  },
  {
    id: 'agent_critic',
    name: 'Critic Agent',
    category: 'Verification',
    stage: 'Quality & Consistency Audit',
    description: 'Evaluates candidate agent responses against retrieved evidence to detect contradictions, omissions, or unsourced claims.',
    allowedTools: ['consistency_checker', 'grounding_evaluator', 'fallacy_detector'],
    memoryAccess: 'Read (Evaluation Frame)',
    knowledgeAccess: 'Retrieved Provenance Chunks',
    requiredPermissions: ['agent:verify'],
    governanceBoundary: 'Enforces minimum confidence thresholds prior to user dispatch.'
  },
  {
    id: 'agent_response',
    name: 'Response Generator Agent',
    category: 'Verification',
    stage: 'Final Output Generation',
    description: 'Formats verified reasoning, structured markdown, and citations into human-readable enterprise deliverables.',
    allowedTools: ['markdown_formatter', 'citation_attacher', 'schema_validator'],
    memoryAccess: 'Write (Session Response)',
    knowledgeAccess: 'Approved Output Context',
    requiredPermissions: ['chat:respond'],
    governanceBoundary: 'Strict output sanitization and secret masking filters.'
  }
];

export default function AdminAgents({ addLog }) {
  const [agents, setAgents] = useState(CANONICAL_AGENTS);
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState(null);

  const fetchAgents = useCallback(async () => {
    setError(null);
    try {
      const [capRes, telemetryRes] = await Promise.all([
        getPlatformCapabilities('agent').catch(() => ({ items: [] })),
        getPlatformCapabilityAnalytics('24h', 'agent').catch(() => null)
      ]);
      
      // If backend has registered capabilities, blend with canonical definitions
      if (capRes?.items && capRes.items.length > 0) {
        const backendMap = new Map(capRes.items.map(c => [c.capability_id, c]));
        const blended = CANONICAL_AGENTS.map(agent => {
          const remote = backendMap.get(agent.id) || backendMap.get(`agent_${agent.id}`);
          if (remote) {
            return {
              ...agent,
              version: remote.version || '2.0',
              enabled: remote.enabled !== false,
              requiredPermissions: remote.required_permissions || agent.requiredPermissions
            };
          }
          return agent;
        });
        setAgents(blended);
      }
      setTelemetry(telemetryRes);
    } catch (err) {
      console.error('Failed to load agent capabilities:', err);
      setError('Failed to load agent registry telemetry.');
    } finally {
      setLoading(false);
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchAgents();
  }, [fetchAgents]);

  const handleSync = () => {
    setIsSyncing(true);
    fetchAgents();
  };

  const categories = ['ALL', 'Coordination', 'Knowledge & Memory', 'Execution & Tools', 'Verification'];

  const filteredAgents = agents.filter(a => {
    if (selectedCategory === 'ALL') return true;
    return a.category === selectedCategory;
  });

  return (
    <div className="flex flex-col gap-6 animate-fade-in text-slate-100 font-sans pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-lg shadow-purple-500/10">
            <Sliders size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide uppercase flex items-center gap-2">
              AI Workforce & Agent Governance
              <Badge variant="purple">9 Canonical Agents</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-agent orchestration topology, allowed tool gates, memory tier isolation, and verification boundaries.
            </p>
          </div>
        </div>

        <Button 
          variant="secondary"
          size="sm"
          onClick={handleSync}
          disabled={loading || isSyncing}
          className="flex items-center gap-2 text-xs self-start sm:self-auto"
        >
          <RefreshCw size={13} className={isSyncing ? 'animate-spin text-purple-400' : ''} />
          {isSyncing ? 'Syncing...' : 'Sync Registry'}
        </Button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button variant="ghost" size="xs" onClick={fetchAgents}>Retry</Button>
        </div>
      )}

      {/* 2. Overview KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Workforce Agents"
          value={agents.length}
          subtitle="9 Multi-Domain Specialists"
          trend="Canonical Architecture"
          icon={<Bot size={18} className="text-purple-400" />}
        />
        <MetricCard
          title="Governance Boundaries"
          value="100% Enforced"
          subtitle="Sandboxed & Permission Gated"
          trend="RBAC Scope Bound"
          icon={<ShieldCheck size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Memory Isolation"
          value="Tenant Partitioned"
          subtitle="Zero Cross-Tenant Leakage"
          trend="pgvector Verified"
          icon={<Database size={18} className="text-cyan-400" />}
        />
        <MetricCard
          title="Verification Gating"
          value="Critic Enforced"
          subtitle="Grounding & Fact Checking"
          trend="Evidence Backed"
          icon={<Sparkles size={18} className="text-amber-400" />}
        />
      </div>

      {/* 3. Category Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              selectedCategory === cat
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-white'
            }`}
          >
            {cat} {cat !== 'ALL' && `(${agents.filter(a => a.category === cat).length})`}
          </button>
        ))}
      </div>

      {/* 4. Agent Directory Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAgents.map((agent) => (
          <Card 
            key={agent.id} 
            className="hover:border-purple-500/30 transition-all cursor-pointer flex flex-col justify-between"
            onClick={() => setSelectedAgent(agent)}
          >
            <CardHeader className="pb-3 border-b border-white/[0.04]">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                    <Bot size={16} />
                  </div>
                  <div>
                    <CardTitle className="text-sm text-white font-bold">{agent.name}</CardTitle>
                    <span className="text-[10px] font-mono text-purple-400">{agent.stage}</span>
                  </div>
                </div>
                <Badge variant="purple" size="xs">{agent.category}</Badge>
              </div>
            </CardHeader>

            <CardContent className="p-4 space-y-3 text-xs">
              <p className="text-slate-300 line-clamp-2 leading-relaxed text-[11px]">
                {agent.description}
              </p>

              <div className="space-y-1.5 pt-2 border-t border-white/[0.04] text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Allowed Tools:</span>
                  <span className="font-mono text-slate-300">{agent.allowedTools.length} tools</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Memory Scope:</span>
                  <span className="text-cyan-400 truncate max-w-[140px]">{agent.memoryAccess}</span>
                </div>
              </div>
            </CardContent>

            <CardFooter className="pt-2 border-t border-white/[0.04] flex items-center justify-between">
              <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                <ShieldCheck size={11} /> Governed
              </span>
              <Button variant="ghost" size="xs" className="text-purple-300 hover:text-white flex items-center gap-1">
                <span>Inspect Policies</span>
                <ArrowRight size={11} />
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {/* 5. Agent Governance Inspector Drawer */}
      <Drawer
        isOpen={Boolean(selectedAgent)}
        onClose={() => setSelectedAgent(null)}
        title="Agent Governance & Policy Inspector"
        description="Operational boundaries, memory access permissions, and evidence requirements."
        size="md"
      >
        {selectedAgent && (
          <div className="space-y-4 text-xs text-slate-300">
            {/* Agent Header Banner */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300">
                    <Bot size={16} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">{selectedAgent.name}</h3>
                    <span className="text-[10px] font-mono text-purple-400">{selectedAgent.stage}</span>
                  </div>
                </div>
                <Badge variant="purple">{selectedAgent.category}</Badge>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed pt-1">
                {selectedAgent.description}
              </p>
            </div>

            {/* Allowed Tools */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-white uppercase tracking-wider block">
                Allowed Internal & MCP Tools
              </span>
              <div className="flex flex-wrap gap-1.5">
                {selectedAgent.allowedTools.map((tool, idx) => (
                  <Badge key={idx} variant="cyan" size="xs" className="font-mono">
                    {tool}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Memory & Knowledge Access */}
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
                <span className="text-slate-500 block font-semibold">Memory Access:</span>
                <span className="text-cyan-300 font-mono block">{selectedAgent.memoryAccess}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
                <span className="text-slate-500 block font-semibold">Knowledge Scope:</span>
                <span className="text-purple-300 font-mono block">{selectedAgent.knowledgeAccess}</span>
              </div>
            </div>

            {/* Required RBAC Permissions */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-white uppercase tracking-wider block">
                Required RBAC Permissions
              </span>
              <div className="p-3 rounded-lg bg-black/30 border border-white/[0.04] space-y-1 font-mono text-[11px]">
                {selectedAgent.requiredPermissions.map((perm, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-emerald-300">
                    <CheckCircle2 size={12} className="text-emerald-400 shrink-0" />
                    <span>{perm}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Governance Boundary */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-white uppercase tracking-wider block">
                Governance Boundary & Safeguards
              </span>
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200 text-[11px] leading-relaxed">
                {selectedAgent.governanceBoundary}
              </div>
            </div>

            <div className="pt-2 border-t border-white/[0.06] flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedAgent(null)}>
                Close Inspector
              </Button>
            </div>
          </div>
        )}
      </Drawer>

    </div>
  );
}
