import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BrainCircuit,
  Bot,
  Database,
  Server,
  Sparkles,
  ArrowRight,
  ArrowUpRight,
  FileText,
  Plus,
  Bookmark,
  Clock,
  TrendingUp,
  Workflow,
  AlertCircle,
  AlertTriangle,
  Activity,
  Play,
  Settings,
  MessageSquare,
  HardDrive,
  ShieldCheck,
  ShieldAlert,
  GitBranch,
  CheckCircle2,
  RefreshCw,
  Send,
  Sliders,
  Layers,
  Check,
  Info,
  ExternalLink,
  Cpu,
  Lock
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
  Timeline,
  CodeBlock
} from '../../components/ui';
import {
  getPlatformStatus,
  getPlatformCapabilities,
  getPlatformOverviewMetrics,
  getPlatformAlerts,
  executeIntelligentQuery,
} from '../../api/platform';
import { listDocuments } from '../../api/documents';
import { getWorkflows } from '../../api/workflows';
import { listMCPServers } from '../../api/mcp';
import { getAdminActivityFeed } from '../../api/admin';

export default function UserDashboard({ triggerNotification }) {
  const navigate = useNavigate();
  const { user, role, workspaceId, isAuthenticated } = useAuth();
  const { theme } = useTheme();

  const isViewer = (role || '').toLowerCase() === 'viewer';
  const isAdminOrOwner = ['admin', 'super admin', 'owner'].includes((role || '').toLowerCase());

  // Platform & Workspace State
  const [platformStatus, setPlatformStatus] = useState(null);
  const [overviewMetrics, setOverviewMetrics] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);

  // Counts for snapshots
  const [documentCount, setDocumentCount] = useState(null);
  const [workflowCount, setWorkflowCount] = useState(null);
  const [mcpServerCount, setMcpServerCount] = useState(null);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  // AI Workspace Input State ("Ask AegisAI")
  const [promptInput, setPromptInput] = useState('');
  const [executionMode, setExecutionMode] = useState('adaptive'); // adaptive | parallel | sequential
  const [selectedSubsystem, setSelectedSubsystem] = useState('all');
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeExecution, setActiveExecution] = useState(null);
  const [executionError, setExecutionError] = useState(null);

  const inputRef = useRef(null);

  // Load all dashboard operational data
  const loadDashboardData = useCallback(async () => {
    setLoadError(null);
    try {
      const [
        statusRes,
        metricsRes,
        capsRes,
        alertsRes,
        activityRes,
        docsRes,
        wfRes,
        mcpRes
      ] = await Promise.allSettled([
        getPlatformStatus(),
        getPlatformOverviewMetrics('24h'),
        getPlatformCapabilities(),
        getPlatformAlerts('24h'),
        getAdminActivityFeed(10),
        listDocuments('ALL', 1, 0),
        getWorkflows({ limit: 1 }),
        listMCPServers({ limit: 1 })
      ]);

      if (statusRes.status === 'fulfilled') setPlatformStatus(statusRes.value);
      if (metricsRes.status === 'fulfilled') setOverviewMetrics(metricsRes.value);
      if (capsRes.status === 'fulfilled') setCapabilities(capsRes.value?.items || []);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value?.alerts || []);
      if (activityRes.status === 'fulfilled') setRecentActivity(activityRes.value?.events || []);

      if (docsRes.status === 'fulfilled') setDocumentCount(docsRes.value?.length ?? 0);
      if (wfRes.status === 'fulfilled') setWorkflowCount(wfRes.value?.total ?? 0);
      if (mcpRes.status === 'fulfilled') setMcpServerCount(mcpRes.value?.total ?? 0);

      setLastSyncTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setLoadError('Failed to load dashboard operational data. Please check your network or retry.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    loadDashboardData();
  };

  // Submit AI Request
  const handlePromptSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!promptInput.trim() || isExecuting || isViewer) return;

    setIsExecuting(true);
    setExecutionError(null);
    setActiveExecution({
      status: 'validating',
      query: promptInput.trim(),
      startedAt: new Date().toISOString(),
      stepIndex: 1
    });

    try {
      // Simulate/Trigger deterministic execution
      const payload = {
        query: promptInput.trim(),
        mode: executionMode,
      };

      const result = await executeIntelligentQuery(payload);
      setActiveExecution({
        status: result.status || 'completed',
        execution_id: result.execution_id,
        query: promptInput.trim(),
        output: result.output,
        confidence: result.confidence,
        confidence_level: result.confidence_level,
        duration_ms: result.duration_ms,
        provenance: result.provenance || [],
        plan: result.plan,
        startedAt: new Date().toISOString(),
        stepIndex: 5
      });

      if (triggerNotification) {
        triggerNotification('Execution Completed', `Intelligence query processed in ${result.duration_ms || 0}ms.`);
      }
      setPromptInput('');
    } catch (err) {
      console.error('AI Execution failed:', err);
      const errMsg = err?.message || 'Intelligence engine request failed.';
      setExecutionError(errMsg);
      setActiveExecution(prev => prev ? { ...prev, status: 'failed', error: errMsg } : null);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handlePromptSubmit();
    }
  };

  const handleFocusAiInput = () => {
    inputRef.current?.focus();
    inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  // Quick Action navigation paths
  const quickActions = [
    { label: 'Ask AegisAI', desc: 'Interactive AI workspace', path: '/user/chat', icon: <Bot size={16} className="text-cyan-400" />, enabled: true },
    { label: 'Build Workflow', desc: 'DAG automation engine', path: '/user/workflows', icon: <Workflow size={16} className="text-purple-400" />, enabled: !isViewer },
    { label: 'Upload Documents', desc: 'Index RAG vector store', path: '/user/documents', icon: <FileText size={16} className="text-blue-400" />, enabled: !isViewer },
    { label: 'Explore Graph', desc: 'Knowledge entity triples', path: '/user/graph', icon: <GitBranch size={16} className="text-teal-400" />, enabled: true },
    { label: 'Connect MCP', desc: 'Manage server daemons', path: '/user/mcp-marketplace', icon: <Server size={16} className="text-amber-400" />, enabled: !isViewer },
    { label: 'Memory Vault', desc: 'Episodic vector memory', path: '/user/memory', icon: <Bookmark size={16} className="text-rose-400" />, enabled: true },
  ];

  // Core System Capabilities Map
  const capabilitiesList = [
    { id: 'agents', name: 'Agent Collective', type: 'MULTI_AGENT', desc: 'Planner, Critic, and Execution swarms in DAG pipelines.', icon: <Bot size={16} className="text-cyan-400" />, path: '/user/ai-marketplace', status: 'ONLINE' },
    { id: 'knowledge', name: 'Knowledge & RAG', type: 'HYBRID_VECTOR', desc: 'Document ingestion, chunking, and verifiable vector citations.', icon: <FileText size={16} className="text-blue-400" />, path: '/user/documents', status: 'ONLINE' },
    { id: 'memory', name: 'Cognitive Memory', type: 'EPISODIC_STORE', desc: 'Isolated vector memories and conversational reflections.', icon: <Database size={16} className="text-purple-400" />, path: '/user/memory', status: 'ONLINE' },
    { id: 'mcp', name: 'MCP Tool Ecosystem', type: 'SANDBOXED_TOOLS', desc: 'Standardized Model Context Protocol servers and capabilities.', icon: <Server size={16} className="text-amber-400" />, path: '/user/mcp-marketplace', status: 'ONLINE' },
    { id: 'workflows', name: 'Workflow Engine', type: 'DAG_AUTOMATION', desc: 'Visual workflow canvas with condition evaluation & replay.', icon: <Workflow size={16} className="text-indigo-400" />, path: '/user/workflows', status: 'ONLINE' },
    { id: 'graph', name: 'Knowledge Graph', type: 'GRAPH_TRIPLES', desc: 'Multi-hop entity relationships and semantic traversals.', icon: <GitBranch size={16} className="text-teal-400" />, path: '/user/graph', status: 'ONLINE' },
    { id: 'platform', name: 'Execution Engine', type: 'VERIFIABLE_EXEC', desc: 'Cryptographic hash chains with zero private secret exposure.', icon: <Activity size={16} className="text-emerald-400" />, path: '/user/platform', status: 'ONLINE' }
  ];

  // 6 System Agents (Architectural Workforce)
  const systemAgents = [
    { name: 'Orchestrator Agent', role: 'Global Swarm Coordinator', status: 'ONLINE' },
    { name: 'Planner Agent', role: 'DAG Task Decomposition', status: 'ONLINE' },
    { name: 'Research Agent', role: 'Hybrid RAG & Vector Lookup', status: 'ONLINE' },
    { name: 'Tool Executor', role: 'Sandboxed MCP Invocation', status: 'ONLINE' },
    { name: 'Critic & Consensus', role: 'Verification & Quality Gate', status: 'ONLINE' },
    { name: 'Response Generator', role: 'Evidence-Backed Synthesis', status: 'ONLINE' }
  ];

  const systemHealth = platformStatus?.system_health || 'ONLINE';

  return (
    <div className="flex flex-col gap-8 animate-fade-in pb-12 font-sans text-slate-100">
      
      {/* ==============================================================================
       * 1. Workspace Header & Mission Control Surface
       * ============================================================================== */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-white uppercase flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
              AegisAI OS — Mission Control
            </h1>
            <Badge variant="cyan" size="sm">
              {role ? role.toUpperCase() : 'MEMBER'}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1.5 flex items-center gap-2">
            <span>Workspace: <strong className="text-slate-200">{workspaceId || 'Default Workspace'}</strong></span>
            <span>•</span>
            <span>Handshake secure</span>
            {lastSyncTime && (
              <>
                <span>•</span>
                <span className="text-slate-500 font-mono text-[11px]">Synced {lastSyncTime}</span>
              </>
            )}
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2.5">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.08] bg-[#0d1017]">
            <span className="text-[10px] uppercase font-mono text-slate-400">System Status:</span>
            <StatusBadge status={systemHealth} size="xs" />
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleManualRefresh}
            isLoading={isRefreshing}
            leftIcon={<RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />}
          >
            Sync
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleFocusAiInput}
            leftIcon={<Sparkles size={14} />}
          >
            Ask AegisAI
          </Button>
        </div>
      </div>

      {/* Viewer Mode Notice */}
      {isViewer && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-3">
          <Info size={16} className="shrink-0" />
          <span>You have <strong>Viewer</strong> access. Workspace data and AI chat are available in read-only inspection mode.</span>
        </div>
      )}

      {/* Global Load Error Banner */}
      {loadError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="shrink-0" />
            <span>{loadError}</span>
          </div>
          <Button variant="ghost" size="xs" onClick={loadDashboardData}>
            Retry
          </Button>
        </div>
      )}

      {/* ==============================================================================
       * 2. Primary AI Workspace Console ("Ask AegisAI")
       * ============================================================================== */}
      <Card className="border-cyan-500/30 bg-gradient-to-b from-[#0d1322]/80 to-[#0a0d16]/80 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <CardHeader className="border-b border-white/[0.08] pb-3.5 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Sparkles size={16} />
            </div>
            <div>
              <CardTitle className="text-sm font-bold text-white uppercase tracking-wider">
                Primary AI Workspace Console
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Dispatch autonomous natural language tasks to the multi-agent orchestration collective.
              </CardDescription>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-mono text-[10px] hidden sm:inline">Execution Mode:</span>
            <div className="flex rounded-lg border border-white/10 bg-white/[0.02] p-0.5">
              {['adaptive', 'parallel', 'sequential'].map((m) => (
                <button
                  key={m}
                  onClick={() => setExecutionMode(m)}
                  className={`px-2.5 py-1 rounded text-[11px] font-mono capitalize transition-all cursor-pointer ${
                    executionMode === m
                      ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-4 flex flex-col gap-4">
          <form onSubmit={handlePromptSubmit} className="flex flex-col gap-3">
            <div className="relative">
              <textarea
                ref={inputRef}
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isExecuting || isViewer}
                placeholder={isViewer ? 'Viewer role — prompt submission disabled' : 'Describe your operational goal, request document synthesis, or trigger an agent workflow...'}
                rows={3}
                className="w-full rounded-xl border border-white/10 bg-[#07090e]/80 p-3.5 text-xs text-slate-100 placeholder:text-slate-500 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all resize-none font-sans leading-relaxed"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                <span>[Enter] to execute</span>
                <span>•</span>
                <span>[Shift+Enter] for newline</span>
                <span>•</span>
                <span>{promptInput.length} chars</span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/user/chat')}
                  leftIcon={<Bot size={13} />}
                >
                  Full AI Chat
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!promptInput.trim() || isExecuting || isViewer}
                  isLoading={isExecuting}
                  rightIcon={<Send size={13} />}
                >
                  Execute Query
                </Button>
              </div>
            </div>
          </form>

          {/* Execution Error Feedback */}
          {executionError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle size={14} className="shrink-0" />
              <span>{executionError}</span>
            </div>
          )}

          {/* Live Execution Timeline / Active Result State */}
          {activeExecution && (
            <div className="mt-2 p-4 rounded-xl border border-cyan-500/20 bg-cyan-500/[0.03] flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 text-xs">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-cyan-400 animate-pulse" />
                  <span className="font-bold text-slate-200">Execution Status</span>
                  {activeExecution.execution_id && (
                    <span className="font-mono text-[10px] text-slate-400">ID: {activeExecution.execution_id}</span>
                  )}
                </div>
                <StatusBadge status={activeExecution.status} size="xs" />
              </div>

              {/* 5-Step Execution Stage Progression */}
              <div className="grid grid-cols-5 gap-2 text-center text-[10px] font-mono py-1">
                {[
                  { label: 'VALIDATING', step: 1 },
                  { label: 'PLANNING', step: 2 },
                  { label: 'EXECUTING', step: 3 },
                  { label: 'VERIFYING', step: 4 },
                  { label: 'COMPLETED', step: 5 },
                ].map((s) => {
                  const isCurrent = (activeExecution.stepIndex || 1) === s.step;
                  const isDone = (activeExecution.stepIndex || 1) >= s.step;
                  return (
                    <div
                      key={s.label}
                      className={`p-1.5 rounded border transition-all ${
                        isDone
                          ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300 font-bold'
                          : 'border-white/5 bg-white/[0.02] text-slate-500'
                      } ${isCurrent ? 'animate-pulse' : ''}`}
                    >
                      {s.label}
                    </div>
                  );
                })}
              </div>

              {/* Result Summary Output */}
              {activeExecution.output && (
                <div className="mt-1 p-3 rounded-lg bg-black/40 border border-white/[0.06] text-xs">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold block mb-1">
                    Evidence-Backed Output:
                  </span>
                  <p className="text-slate-200 leading-relaxed">
                    {activeExecution.output.summary || JSON.stringify(activeExecution.output)}
                  </p>
                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/[0.04] text-[10px] font-mono text-slate-400">
                    <span>Evidence Items: {activeExecution.provenance?.length ?? 0}</span>
                    <span>Confidence: {activeExecution.confidence_level || 'HIGH'} ({Math.round((activeExecution.confidence || 0.9) * 100)}%)</span>
                    <span>Duration: {activeExecution.duration_ms || 0}ms</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ==============================================================================
       * 3. Operational Quick Actions Strip
       * ============================================================================== */}
      <div>
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Sparkles size={13} className="text-cyan-400" /> Operational Quick Actions
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={() => action.enabled && navigate(action.path)}
              disabled={!action.enabled}
              className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between min-h-[90px] ${
                action.enabled
                  ? 'border-white/[0.08] bg-[#0d1017]/80 hover:border-cyan-500/30 hover:-translate-y-0.5 cursor-pointer'
                  : 'border-white/5 bg-white/[0.01] opacity-50 cursor-not-allowed'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <div className="p-1.5 rounded-lg bg-white/5 border border-white/5">
                  {action.icon}
                </div>
                <ArrowUpRight size={12} className="text-slate-500" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-white mt-2">{action.label}</h3>
                <p className="text-[10px] text-slate-500 leading-tight line-clamp-1">{action.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ==============================================================================
       * 4. Attention Center
       * ============================================================================== */}
      <div>
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <AlertCircle size={13} className="text-amber-400" /> Workspace Attention Center
        </h2>

        {alerts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {alerts.map((alert) => (
              <div
                key={alert.alert_id}
                className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 flex items-start justify-between gap-3 text-xs"
              >
                <div className="flex items-start gap-2.5">
                  <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-amber-200">{alert.title}</h4>
                    <p className="text-slate-400 text-[11px] mt-1">{alert.description}</p>
                  </div>
                </div>
                <Badge variant="warning" size="xs">
                  {alert.severity}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] flex items-center gap-3 text-xs text-slate-300">
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
            <span>Nothing requires your attention. All workspace subsystems and agent execution loops are operating nominally.</span>
          </div>
        )}
      </div>

      {/* ==============================================================================
       * 5. Capability Map Overview
       * ============================================================================== */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Cpu size={13} className="text-purple-400" /> Autonomous Platform Capabilities
          </h2>
          <button
            onClick={() => navigate('/user/platform')}
            className="text-xs text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer font-mono"
          >
            Explore All <ArrowRight size={12} />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {capabilitiesList.map((cap) => (
            <Card
              key={cap.id}
              onClick={() => navigate(cap.path)}
              className="border-white/[0.08] bg-[#0d1017]/80 hover:border-cyan-500/30 transition-all cursor-pointer"
            >
              <CardContent className="p-4 flex flex-col justify-between min-h-[120px]">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-white/5 border border-white/5">{cap.icon}</div>
                    <div>
                      <h4 className="text-xs font-bold text-white">{cap.name}</h4>
                      <span className="text-[9px] font-mono text-cyan-400">{cap.type}</span>
                    </div>
                  </div>
                  <StatusBadge status={cap.status} size="xs" />
                </div>
                <p className="text-[11px] text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                  {cap.desc}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* ==============================================================================
       * 6. Multi-Domain Intelligence Snapshots (2-Column Grid)
       * ============================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Knowledge & Memory Snapshot */}
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Database size={15} className="text-blue-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                Knowledge & Cognitive Memory Snapshot
              </CardTitle>
            </div>
            <Button variant="ghost" size="xs" onClick={() => navigate('/user/documents')}>
              Open Hub
            </Button>
          </CardHeader>
          <CardContent className="p-4 flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                <span className="text-[10px] text-slate-500 block">DOCUMENTS INDEXED</span>
                <span className="text-base font-bold text-white mt-1 block">
                  {documentCount !== null ? documentCount : 'Available'}
                </span>
                <span className="text-[9px] text-emerald-400">RAG Ready</span>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                <span className="text-[10px] text-slate-500 block">MEMORY VAULT</span>
                <span className="text-base font-bold text-white mt-1 block">Vectorized</span>
                <span className="text-[9px] text-purple-400">Workspace Isolated</span>
              </div>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Hybrid vector search indexing documents alongside episodic reflections. Cross-tenant leakage is strictly blocked at the database engine boundary.
            </p>
          </CardContent>
        </Card>

        {/* Agent Workforce Snapshot */}
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot size={15} className="text-cyan-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                Active System Agent Workforce
              </CardTitle>
            </div>
            <Badge variant="neutral" size="xs">SYSTEM AGENTS</Badge>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {systemAgents.map((ag) => (
                <div key={ag.name} className="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 text-left">
                  <span className="text-[11px] font-bold text-slate-200 block truncate">{ag.name}</span>
                  <span className="text-[9px] text-slate-500 block truncate">{ag.role}</span>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span className="text-[9px] font-mono text-emerald-400">ONLINE</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* MCP Ecosystem Snapshot */}
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Server size={15} className="text-amber-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                MCP Tool Ecosystem Snapshot
              </CardTitle>
            </div>
            <Button variant="ghost" size="xs" onClick={() => navigate('/user/mcp-marketplace')}>
              Open MCP Center
            </Button>
          </CardHeader>
          <CardContent className="p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-slate-300 font-semibold">Registered MCP Daemons</span>
              </div>
              <span className="font-mono font-bold text-white">
                {mcpServerCount !== null ? mcpServerCount : 'Connected'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Standardized Model Context Protocol servers allowing agents to safely invoke approved tools with human-in-the-loop gates.
            </p>
          </CardContent>
        </Card>

        {/* Workflow Automation Snapshot */}
        <Card className="border-white/[0.08] bg-[#0d1017]/80">
          <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Workflow size={15} className="text-purple-400" />
              <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
                Workflow Automation Snapshot
              </CardTitle>
            </div>
            <Button variant="ghost" size="xs" onClick={() => navigate('/user/workflows')}>
              Workflow Builder
            </Button>
          </CardHeader>
          <CardContent className="p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-purple-400" />
                <span className="text-slate-300 font-semibold">Active Workflows</span>
              </div>
              <span className="font-mono font-bold text-white">
                {workflowCount !== null ? workflowCount : 'Available'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Visual DAG orchestration supporting human approvals, parallel agent branches, and deterministic execution replays.
            </p>
          </CardContent>
        </Card>

      </div>

      {/* ==============================================================================
       * 7. Recent Operational Activity Feed
       * ============================================================================== */}
      <Card className="border-white/[0.08] bg-[#0d1017]/80">
        <CardHeader className="border-b border-white/[0.06] pb-3 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={15} className="text-purple-400" />
            <CardTitle className="text-xs font-bold text-white uppercase tracking-wider">
              Recent Operational Activity Feed
            </CardTitle>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Live Workspace Log</span>
        </CardHeader>
        <CardContent className="p-4">
          {recentActivity.length > 0 ? (
            <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
              {recentActivity.map((act, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs font-mono"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0" />
                    <span className="text-slate-200">{act.summary}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-slate-500 shrink-0">
                    <span className="bg-white/5 px-2 py-0.5 rounded">{act.source_component || 'SYS'}</span>
                    <span>{new Date(act.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Clock size={20} />}
              title="No recent activity"
              description="Your workspace activity stream is clean. Start an agent execution or workflow to see live events."
            />
          )}
        </CardContent>
      </Card>

    </div>
  );
}
