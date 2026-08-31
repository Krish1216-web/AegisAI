import React, { useState, useEffect, useMemo } from 'react';
import { 
  Server, 
  Search, 
  RefreshCw, 
  Plus, 
  Trash2, 
  CheckCircle, 
  AlertCircle, 
  Wrench, 
  FileCode, 
  MessageSquare, 
  X, 
  Power, 
  ChevronRight, 
  Code, 
  Activity, 
  Tag, 
  AlertTriangle,
  Shield,
  Layers,
  CheckCircle2,
  XCircle,
  Play,
  Copy,
  Clock,
  Star,
  History,
  BarChart3,
  ExternalLink,
  Lock,
  Check,
  Filter,
  Eye,
  Sliders
} from 'lucide-react';
import {
  listMCPServers,
  registerMCPServer,
  deleteMCPServer,
  refreshServerDiscovery,
  checkServerHealth,
  listServerCapabilities,
  enableMCPServer,
  disableMCPServer,
  listWorkspaceTools,
  searchWorkspaceTools,
  getToolDetails,
  executeMCPTool,
  generateToolConfirmationToken,
  enableMCPTool,
  disableMCPTool,
  listMCPResources,
  searchMCPResources,
  readMCPResource,
  enableMCPResource,
  disableMCPResource,
  listMCPPrompts,
  searchMCPPrompts,
  renderMCPPrompt,
  enableMCPPrompt,
  disableMCPPrompt,
  getMCPSecurityStatus,
  getMCPSecurityAuditLog,
  getMCPOverviewMetrics,
  getMCPExecutionHistory
} from '../../api/mcp';

export default function UserMcpMarket({ triggerNotification }) {
  // Top Level Navigation: 'overview' | 'servers' | 'tools' | 'resources' | 'prompts' | 'security' | 'history' | 'audit'
  const [activeMode, setActiveMode] = useState('overview');

  // Favorites / Pinning state persisted to localStorage
  const [pinnedTools, setPinnedTools] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('aegis_pinned_mcp_tools') || '[]');
    } catch {
      return [];
    }
  });
  const [pinnedServers, setPinnedServers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('aegis_pinned_mcp_servers') || '[]');
    } catch {
      return [];
    }
  });

  const togglePinTool = (id) => {
    setPinnedTools((prev) => {
      const next = prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id];
      localStorage.setItem('aegis_pinned_mcp_tools', JSON.stringify(next));
      return next;
    });
  };

  const togglePinServer = (id) => {
    setPinnedServers((prev) => {
      const next = prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id];
      localStorage.setItem('aegis_pinned_mcp_servers', JSON.stringify(next));
      return next;
    });
  };

  // Overview Dashboard State
  const [overviewMetrics, setOverviewMetrics] = useState(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState(false);

  // Security & Audit State
  const [securityStatus, setSecurityStatus] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isLoadingSecurity, setIsLoadingSecurity] = useState(false);
  const [auditDecisionFilter, setAuditDecisionFilter] = useState('all');
  const [auditSearchQuery, setAuditSearchQuery] = useState('');

  // Execution History State
  const [executionHistory, setExecutionHistory] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyStatusFilter, setHistoryStatusFilter] = useState('all');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [showExecutionDetailModal, setShowExecutionDetailModal] = useState(false);

  // Servers State
  const [servers, setServers] = useState([]);
  const [isLoadingServers, setIsLoadingServers] = useState(true);
  const [serverSearch, setServerSearch] = useState('');
  const [serverFilterPinned, setServerFilterPinned] = useState(false);
  
  // Registration Modal State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [name, setName] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [transport, setTransport] = useState('sse');
  const [authType, setAuthType] = useState('none');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Capabilities View Modal State
  const [showCapabilitiesModal, setShowCapabilitiesModal] = useState(false);
  const [selectedServer, setSelectedServer] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [activeCapTab, setActiveCapTab] = useState('tool');
  const [capSearch, setCapSearch] = useState('');
  const [isLoadingCaps, setIsLoadingCaps] = useState(false);
  const [selectedCap, setSelectedCap] = useState(null);

  // Discovery Summary Modal
  const [discoverySummary, setDiscoverySummary] = useState(null);

  // Tool Catalog & Execution State
  const [tools, setTools] = useState([]);
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [toolSearchQuery, setToolSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('all');
  const [toolFilterPinned, setToolFilterPinned] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const [showToolModal, setShowToolModal] = useState(false);
  const [toolModalTab, setToolModalTab] = useState('schema'); // 'schema' | 'execute'
  const [executionArgs, setExecutionArgs] = useState({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [executionError, setExecutionError] = useState(null);
  const [restrictedConfirmed, setRestrictedConfirmed] = useState(false);
  const [copiedResult, setCopiedResult] = useState(false);

  // In-flight state trackers
  const [discoveringIds, setDiscoveringIds] = useState(new Set());
  const [healthCheckingIds, setHealthCheckingIds] = useState(new Set());
  const [healthMetrics, setHealthMetrics] = useState({});

  // Resources State
  const [resources, setResources] = useState([]);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [resourceSearchQuery, setResourceSearchQuery] = useState('');
  const [selectedResource, setSelectedResource] = useState(null);
  const [showResourceModal, setShowResourceModal] = useState(false);
  const [isReadingResource, setIsReadingResource] = useState(false);
  const [resourceContent, setResourceContent] = useState(null);
  const [resourceReadError, setResourceReadError] = useState(null);

  // Prompts State
  const [prompts, setPrompts] = useState([]);
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(false);
  const [promptSearchQuery, setPromptSearchQuery] = useState('');
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [isRenderingPrompt, setIsRenderingPrompt] = useState(false);
  const [promptArgs, setPromptArgs] = useState({});
  const [renderedPrompt, setRenderedPrompt] = useState(null);
  const [promptRenderError, setPromptRenderError] = useState(null);

  // Fetch Overview Metrics
  const fetchOverviewMetrics = async () => {
    setIsLoadingOverview(true);
    try {
      const data = await getMCPOverviewMetrics();
      setOverviewMetrics(data);
    } catch (err) {
      console.error('Failed to load overview metrics:', err);
    } finally {
      setIsLoadingOverview(false);
    }
  };

  // Fetch Servers
  const fetchServers = async () => {
    setIsLoadingServers(true);
    try {
      const data = await listMCPServers();
      setServers(data.servers || []);
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
      triggerNotification?.('Error', 'Failed to load MCP servers.');
    } finally {
      setIsLoadingServers(false);
    }
  };

  // Fetch Tools
  const fetchTools = async () => {
    setIsLoadingTools(true);
    try {
      if (toolSearchQuery.trim()) {
        const data = await searchWorkspaceTools({
          query: toolSearchQuery.trim(),
          risk_level: selectedRiskFilter !== 'all' ? selectedRiskFilter : undefined,
          enabled_only: false,
          include_stale: true,
          limit: 100
        });
        setTools(data.results || []);
      } else {
        const data = await listWorkspaceTools({
          risk_level: selectedRiskFilter !== 'all' ? selectedRiskFilter : undefined,
          include_stale: true,
          limit: 100
        });
        setTools(data.tools || []);
      }
    } catch (err) {
      console.error('Failed to load tools:', err);
      triggerNotification?.('Error', 'Failed to load MCP tools catalog.');
    } finally {
      setIsLoadingTools(false);
    }
  };

  // Fetch Resources
  const fetchResources = async () => {
    setIsLoadingResources(true);
    try {
      if (resourceSearchQuery.trim()) {
        const data = await searchMCPResources({
          query: resourceSearchQuery.trim(),
          enabled_only: false,
          include_stale: true,
          limit: 50
        });
        setResources(data.results || []);
      } else {
        const data = await listMCPResources({
          include_stale: true,
          limit: 100
        });
        setResources(data.resources || []);
      }
    } catch (err) {
      console.error('Failed to load resources:', err);
      triggerNotification?.('Error', 'Failed to load MCP resources catalog.');
    } finally {
      setIsLoadingResources(false);
    }
  };

  // Fetch Prompts
  const fetchPrompts = async () => {
    setIsLoadingPrompts(true);
    try {
      if (promptSearchQuery.trim()) {
        const data = await searchMCPPrompts({
          query: promptSearchQuery.trim(),
          enabled_only: false,
          include_stale: true,
          limit: 50
        });
        setPrompts(data.results || []);
      } else {
        const data = await listMCPPrompts({
          include_stale: true,
          limit: 100
        });
        setPrompts(data.prompts || []);
      }
    } catch (err) {
      console.error('Failed to load prompts:', err);
      triggerNotification?.('Error', 'Failed to load MCP prompts catalog.');
    } finally {
      setIsLoadingPrompts(false);
    }
  };

  // Fetch Security Data
  const fetchSecurityData = async () => {
    setIsLoadingSecurity(true);
    try {
      const [statusRes, auditRes] = await Promise.all([
        getMCPSecurityStatus(),
        getMCPSecurityAuditLog(100)
      ]);
      setSecurityStatus(statusRes);
      setAuditLogs(auditRes.events || []);
    } catch (err) {
      console.error('Failed to load MCP security data:', err);
      triggerNotification?.('Error', 'Failed to load MCP security status.');
    } finally {
      setIsLoadingSecurity(false);
    }
  };

  // Fetch Execution History
  const fetchExecutionHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const data = await getMCPExecutionHistory({
        status: historyStatusFilter !== 'all' ? historyStatusFilter : undefined,
        limit: 100
      });
      setExecutionHistory(data.executions || []);
      setHistoryTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load execution history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Initial loads and mode transitions
  useEffect(() => {
    fetchOverviewMetrics();
    fetchServers();
  }, []);

  useEffect(() => {
    if (activeMode === 'overview') {
      fetchOverviewMetrics();
    } else if (activeMode === 'servers') {
      fetchServers();
    } else if (activeMode === 'tools') {
      const timer = setTimeout(() => fetchTools(), 200);
      return () => clearTimeout(timer);
    } else if (activeMode === 'resources') {
      const timer = setTimeout(() => fetchResources(), 200);
      return () => clearTimeout(timer);
    } else if (activeMode === 'prompts') {
      const timer = setTimeout(() => fetchPrompts(), 200);
      return () => clearTimeout(timer);
    } else if (activeMode === 'security' || activeMode === 'audit') {
      fetchSecurityData();
    } else if (activeMode === 'history') {
      fetchExecutionHistory();
    }
  }, [activeMode, toolSearchQuery, selectedRiskFilter, resourceSearchQuery, promptSearchQuery, historyStatusFilter]);

  // Server Handlers
  const handleRegister = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!name.trim() || !serverUrl.trim()) {
      setFormError('Server name and connection URL are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      await registerMCPServer({
        name: name.trim(),
        server_url: serverUrl.trim(),
        transport,
        authentication_type: authType,
        description: description.trim() || undefined
      });
      triggerNotification?.('Success', `Registered MCP server '${name}'`);
      setShowRegisterModal(false);
      setName('');
      setServerUrl('');
      setDescription('');
      fetchServers();
      fetchOverviewMetrics();
    } catch (err) {
      setFormError(err.message || 'Failed to register server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleEnable = async (server) => {
    try {
      if (server.enabled) {
        await disableMCPServer(server.id);
        triggerNotification?.('Server Disabled', `Disabled '${server.name}'`);
      } else {
        await enableMCPServer(server.id);
        triggerNotification?.('Server Enabled', `Enabled '${server.name}'`);
      }
      fetchServers();
      fetchOverviewMetrics();
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to toggle server state.');
    }
  };

  const handleDelete = async (server) => {
    if (!window.confirm(`Are you sure you want to delete MCP server '${server.name}'?`)) return;
    try {
      await deleteMCPServer(server.id);
      triggerNotification?.('Deleted', `Removed MCP server '${server.name}'`);
      fetchServers();
      fetchOverviewMetrics();
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to delete server.');
    }
  };

  const handleHealthCheck = async (server) => {
    setHealthCheckingIds(prev => new Set(prev).add(server.id));
    try {
      const res = await checkServerHealth(server.id);
      setHealthMetrics(prev => ({ ...prev, [server.id]: res }));
      triggerNotification?.(
        res.is_healthy ? 'Health Check Passed' : 'Health Check Failed',
        res.is_healthy 
          ? `Server '${server.name}' is healthy (${res.latency_ms}ms latency)` 
          : `Server '${server.name}' returned error: ${res.error}`
      );
      fetchServers();
      fetchOverviewMetrics();
    } catch (err) {
      triggerNotification?.('Health Check Error', err.message || 'Failed to execute health check');
    } finally {
      setHealthCheckingIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const handleRefreshDiscovery = async (server) => {
    setDiscoveringIds(prev => new Set(prev).add(server.id));
    try {
      const res = await refreshServerDiscovery(server.id, true);
      setDiscoverySummary(res);
      triggerNotification?.(
        'Discovery Refreshed',
        `Discovered ${res.total_tools} tools, ${res.total_resources} resources, ${res.total_prompts} prompts.`
      );
      fetchServers();
      fetchOverviewMetrics();
    } catch (err) {
      triggerNotification?.('Discovery Error', err.message || 'Failed to run discovery refresh');
    } finally {
      setDiscoveringIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const handleOpenCapabilities = async (server) => {
    setSelectedServer(server);
    setSelectedCap(null);
    setShowCapabilitiesModal(true);
    setIsLoadingCaps(true);
    try {
      const data = await listServerCapabilities(server.id, undefined, undefined, true, 200, 0);
      setCapabilities(data.capabilities || []);
    } catch (err) {
      console.error('Failed to load server capabilities:', err);
      triggerNotification?.('Error', 'Failed to retrieve server capabilities.');
    } finally {
      setIsLoadingCaps(false);
    }
  };

  // Tool Handlers
  const handleToggleToolEnable = async (tool) => {
    try {
      if (tool.enabled) {
        await disableMCPTool(tool.id);
        triggerNotification?.('Tool Disabled', `Disabled '${tool.name}'`);
      } else {
        await enableMCPTool(tool.id);
        triggerNotification?.('Tool Enabled', `Enabled '${tool.name}'`);
      }
      fetchTools();
      if (selectedTool && selectedTool.id === tool.id) {
        setSelectedTool(prev => ({ ...prev, enabled: !prev.enabled }));
      }
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to toggle tool state.');
    }
  };

  const handleOpenToolModal = (tool) => {
    setSelectedTool(tool);
    setToolModalTab('schema');
    setExecutionResult(null);
    setExecutionError(null);
    setRestrictedConfirmed(false);
    setCopiedResult(false);
    
    // Initialize default execution arguments from input schema
    const initialArgs = {};
    const props = tool.input_schema?.properties || {};
    Object.keys(props).forEach((key) => {
      const prop = props[key];
      if (prop.default !== undefined) {
        initialArgs[key] = prop.default;
      } else if (prop.type === 'number' || prop.type === 'integer') {
        initialArgs[key] = 0;
      } else if (prop.type === 'boolean') {
        initialArgs[key] = false;
      } else if (prop.type === 'array') {
        initialArgs[key] = [];
      } else if (prop.type === 'object') {
        initialArgs[key] = {};
      } else {
        initialArgs[key] = '';
      }
    });
    setExecutionArgs(initialArgs);
    setShowToolModal(true);
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);
    setCopiedResult(false);

    try {
      let confToken = undefined;
      // Handle confirmation for restricted tools
      if (selectedTool.risk_level === 'restricted' || selectedTool.policy_decision === 'require_confirmation') {
        if (!restrictedConfirmed) {
          throw new Error('Please confirm the risk warning checkbox before executing this restricted operation.');
        }
        const confRes = await generateToolConfirmationToken(selectedTool.id, executionArgs);
        confToken = confRes.token;
      }

      const res = await executeMCPTool(selectedTool.id, {
        arguments: executionArgs,
        confirmation_token: confToken,
        timeout: 20
      });

      setExecutionResult(res);
      triggerNotification?.('Execution Succeeded', `Tool '${selectedTool.name}' ran in ${res.duration_ms}ms`);
      fetchExecutionHistory();
      fetchOverviewMetrics();
    } catch (err) {
      console.error('Tool execution error:', err);
      setExecutionError(err.message || 'Execution failed.');
      triggerNotification?.('Execution Error', err.message || 'Failed to execute tool.');
    } finally {
      setIsExecuting(false);
    }
  };

  // Resource Handlers
  const handleOpenResource = async (resource) => {
    setSelectedResource(resource);
    setShowResourceModal(true);
    setIsReadingResource(true);
    setResourceContent(null);
    setResourceReadError(null);

    try {
      const res = await readMCPResource(resource.id, 20);
      setResourceContent(res);
    } catch (err) {
      console.error('Resource read error:', err);
      setResourceReadError(err.message || 'Failed to read resource content.');
    } finally {
      setIsReadingResource(false);
    }
  };

  // Prompt Handlers
  const handleOpenPrompt = (prompt) => {
    setSelectedPrompt(prompt);
    setShowPromptModal(true);
    setRenderedPrompt(null);
    setPromptRenderError(null);

    // Initialize prompt arguments
    const initArgs = {};
    (prompt.arguments || []).forEach(arg => {
      initArgs[arg.name] = '';
    });
    setPromptArgs(initArgs);
  };

  const handleRenderPrompt = async () => {
    if (!selectedPrompt) return;
    setIsRenderingPrompt(true);
    setPromptRenderError(null);
    setRenderedPrompt(null);

    try {
      const res = await renderMCPPrompt(selectedPrompt.id, promptArgs, 20);
      setRenderedPrompt(res);
      triggerNotification?.('Prompt Rendered', `Template '${selectedPrompt.name}' rendered ${res.messages.length} messages.`);
    } catch (err) {
      console.error('Prompt render error:', err);
      setPromptRenderError(err.message || 'Failed to render prompt template.');
    } finally {
      setIsRenderingPrompt(false);
    }
  };

  // Filtered Lists
  const filteredServers = useMemo(() => {
    let list = servers.filter(s => 
      s.name.toLowerCase().includes(serverSearch.toLowerCase()) ||
      s.server_url.toLowerCase().includes(serverSearch.toLowerCase()) ||
      (s.description && s.description.toLowerCase().includes(serverSearch.toLowerCase()))
    );
    if (serverFilterPinned) {
      list = list.filter(s => pinnedServers.includes(s.id));
    }
    return list;
  }, [servers, serverSearch, serverFilterPinned, pinnedServers]);

  const filteredTools = useMemo(() => {
    let list = tools;
    if (toolFilterPinned) {
      list = list.filter(t => pinnedTools.includes(t.id));
    }
    return list;
  }, [tools, toolFilterPinned, pinnedTools]);

  const filteredAuditLogs = useMemo(() => {
    let list = auditLogs;
    if (auditDecisionFilter !== 'all') {
      list = list.filter(e => e.decision === auditDecisionFilter);
    }
    if (auditSearchQuery.trim()) {
      const q = auditSearchQuery.toLowerCase();
      list = list.filter(e => 
        e.operation.toLowerCase().includes(q) ||
        (e.capability_id && e.capability_id.toLowerCase().includes(q)) ||
        (e.reason_code && e.reason_code.toLowerCase().includes(q))
      );
    }
    return list;
  }, [auditLogs, auditDecisionFilter, auditSearchQuery]);

  return (
    <div className="flex flex-col gap-6 text-slate-300 animate-fade-in max-w-7xl mx-auto pb-12">
      
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-1">
            <Layers className="w-3.5 h-3.5" />
            <span>AegisAI Cognitive Engine &bull; Extensible Platform</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Server className="w-6 h-6 text-indigo-400" />
            MCP Control Center &amp; Tool Hub
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Centrally manage Model Context Protocol servers, execute verified tools, preview workspace resources, test prompt templates, and inspect security audit policies.
          </p>
        </div>

        {/* Global Refresh Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (activeMode === 'overview') fetchOverviewMetrics();
              else if (activeMode === 'servers') fetchServers();
              else if (activeMode === 'tools') fetchTools();
              else if (activeMode === 'resources') fetchResources();
              else if (activeMode === 'prompts') fetchPrompts();
              else if (activeMode === 'security' || activeMode === 'audit') fetchSecurityData();
              else if (activeMode === 'history') fetchExecutionHistory();
            }}
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white rounded-xl text-xs flex items-center gap-1.5 transition"
            title="Refresh current view data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center bg-slate-900/90 border border-slate-800 p-1.5 rounded-2xl overflow-x-auto gap-1 shadow-inner scrollbar-none">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'servers', label: `Servers (${servers.length})`, icon: Server },
          { id: 'tools', label: 'Tool Catalog', icon: Wrench },
          { id: 'resources', label: 'Resources', icon: FileCode },
          { id: 'prompts', label: 'Prompts', icon: MessageSquare },
          { id: 'security', label: 'Security & RBAC', icon: Shield },
          { id: 'history', label: `Execution History (${historyTotal})`, icon: History },
          { id: 'audit', label: `Audit Log (${auditLogs.length})`, icon: Clock }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeMode === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveMode(tab.id)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* 1. OVERVIEW DASHBOARD */}
      {/* ========================================================================= */}
      {activeMode === 'overview' && (
        <div className="space-y-6 animate-fade-in">
          {/* Live Status Banner */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-purple-950/40 border border-indigo-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                <Activity className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>MCP Gateway &amp; Cognitive Subsystem</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    OPERATIONAL
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Real-time synchronization with active LangGraph Multi-Agent cognitive pipeline and tenant policy enforcement.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-slate-400 bg-slate-950/60 px-4 py-2 rounded-xl border border-slate-800">
              <div>
                <span className="text-[10px] text-slate-500 block">LAST DISCOVERY</span>
                <span className="text-slate-200">{overviewMetrics?.health.last_discovery_at ? new Date(overviewMetrics.health.last_discovery_at).toLocaleTimeString() : 'Ready'}</span>
              </div>
              <div className="w-px h-6 bg-slate-800" />
              <div>
                <span className="text-[10px] text-slate-500 block">HEALTH PROBE</span>
                <span className="text-slate-200">{overviewMetrics?.health.last_health_check_at ? new Date(overviewMetrics.health.last_health_check_at).toLocaleTimeString() : 'Active'}</span>
              </div>
            </div>
          </div>

          {/* Metric KPI Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Servers KPI */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">MCP Servers</span>
                <Server className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-baseline gap-2 mt-3">
                <span className="text-3xl font-bold text-white font-mono">{overviewMetrics?.servers.total ?? servers.length}</span>
                <span className="text-xs text-emerald-400 font-medium">
                  {overviewMetrics?.servers.active ?? servers.filter(s => s.status === 'active').length} active
                </span>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                <span>{overviewMetrics?.servers.disabled ?? 0} disabled</span>
                <span>&bull;</span>
                <span className={overviewMetrics?.servers.error ? 'text-rose-400' : 'text-slate-500'}>
                  {overviewMetrics?.servers.error ?? 0} error
                </span>
              </div>
            </div>

            {/* Discovered Capabilities KPI */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Discovered Capabilities</span>
                <Layers className="w-4 h-4 text-purple-400" />
              </div>
              <div className="flex items-baseline gap-2 mt-3">
                <span className="text-3xl font-bold text-white font-mono">
                  {(overviewMetrics?.capabilities.total_tools ?? 0) + (overviewMetrics?.capabilities.total_resources ?? 0) + (overviewMetrics?.capabilities.total_prompts ?? 0)}
                </span>
                <span className="text-xs text-purple-400 font-medium">
                  {overviewMetrics?.capabilities.enabled_capabilities ?? 0} enabled
                </span>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 font-mono">
                <span>{overviewMetrics?.capabilities.total_tools ?? 0} tools</span>
                <span>&bull;</span>
                <span>{overviewMetrics?.capabilities.total_resources ?? 0} res</span>
                <span>&bull;</span>
                <span>{overviewMetrics?.capabilities.total_prompts ?? 0} prm</span>
              </div>
            </div>

            {/* Security Decisions KPI */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Security Decisions</span>
                <Shield className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex items-baseline gap-2 mt-3">
                <span className="text-3xl font-bold text-white font-mono">
                  {overviewMetrics?.security.recent_events_count ?? auditLogs.length}
                </span>
                <span className="text-xs text-emerald-400 font-medium">
                  {overviewMetrics?.security.allowed_operations ?? 0} allowed
                </span>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                <span className="text-amber-400">{overviewMetrics?.security.confirmation_required_operations ?? 0} gated</span>
                <span>&bull;</span>
                <span className={overviewMetrics?.security.denied_operations ? 'text-rose-400' : 'text-slate-500'}>
                  {overviewMetrics?.security.denied_operations ?? 0} denied
                </span>
              </div>
            </div>

            {/* Tool Executions KPI */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tool Executions</span>
                <History className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex items-baseline gap-2 mt-3">
                <span className="text-3xl font-bold text-white font-mono">{overviewMetrics?.execution.total ?? historyTotal}</span>
                <span className="text-xs text-emerald-400 font-medium">
                  {overviewMetrics?.execution.successful ?? 0} ok
                </span>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                <span className={overviewMetrics?.execution.failed ? 'text-rose-400' : 'text-slate-500'}>
                  {overviewMetrics?.execution.failed ?? 0} failed
                </span>
                <span>&bull;</span>
                <span>{overviewMetrics?.execution.requires_confirmation ?? 0} confirmed</span>
              </div>
            </div>
          </div>

          {/* Quick Launch Cards */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Subsystem Navigation &amp; Tool Hub</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div 
                onClick={() => setActiveMode('servers')}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/40 hover:bg-slate-900/90 transition cursor-pointer flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3 group-hover:scale-110 transition">
                    <Server className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-bold text-white">Server Registry</h4>
                  <p className="text-xs text-slate-400 mt-1">Connect, monitor, and refresh discovery for stdio, SSE, and HTTP transport servers.</p>
                </div>
                <div className="flex items-center text-xs font-semibold text-indigo-400 mt-4 gap-1">
                  <span>Manage Servers ({servers.length})</span>
                  <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition" />
                </div>
              </div>

              <div 
                onClick={() => setActiveMode('tools')}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-purple-500/40 hover:bg-slate-900/90 transition cursor-pointer flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center mb-3 group-hover:scale-110 transition">
                    <Wrench className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-bold text-white">Tool Catalog &amp; Runner</h4>
                  <p className="text-xs text-slate-400 mt-1">Browse schemas, evaluate risk classifications, and execute tools with single-use confirmation tokens.</p>
                </div>
                <div className="flex items-center text-xs font-semibold text-purple-400 mt-4 gap-1">
                  <span>Browse Tools</span>
                  <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition" />
                </div>
              </div>

              <div 
                onClick={() => setActiveMode('security')}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 hover:bg-slate-900/90 transition cursor-pointer flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-3 group-hover:scale-110 transition">
                    <Shield className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-bold text-white">Security &amp; Audit Log</h4>
                  <p className="text-xs text-slate-400 mt-1">Audit trust boundaries (UNTRUSTED_MCP), active RBAC privileges, and security events.</p>
                </div>
                <div className="flex items-center text-xs font-semibold text-emerald-400 mt-4 gap-1">
                  <span>View Security Dashboard</span>
                  <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. SERVERS REGISTRY */}
      {/* ========================================================================= */}
      {activeMode === 'servers' && (
        <div className="space-y-5 animate-fade-in">
          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={serverSearch}
                  onChange={(e) => setServerSearch(e.target.value)}
                  placeholder="Search registered servers..."
                  className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
                />
              </div>
              <button
                onClick={() => setServerFilterPinned(!serverFilterPinned)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition ${
                  serverFilterPinned
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
                title="Filter Pinned"
              >
                <Star className={`w-3.5 h-3.5 ${serverFilterPinned ? 'fill-amber-400 text-amber-400' : ''}`} />
                <span className="hidden sm:inline">Pinned</span>
              </button>
            </div>

            <button
              onClick={() => setShowRegisterModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>Add MCP Server</span>
            </button>
          </div>

          {/* Servers Grid */}
          {isLoadingServers ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP server registry...</span>
            </div>
          ) : filteredServers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <Server className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No MCP Servers Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Register a server to start discovering dynamic capabilities.</p>
              <button
                onClick={() => setShowRegisterModal(true)}
                className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Register Server</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredServers.map((server) => {
                const isDiscovering = discoveringIds.has(server.id);
                const isHealthChecking = healthCheckingIds.has(server.id);
                const isPinned = pinnedServers.includes(server.id);

                const statusBg = 
                  server.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                  server.status === 'error' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                  server.status === 'disabled' || !server.enabled ? 'bg-slate-800 text-slate-400 border-slate-700' :
                  'bg-amber-500/10 text-amber-400 border-amber-500/20';

                return (
                  <div 
                    key={server.id} 
                    className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                      server.enabled ? 'border-slate-800 hover:border-slate-700 shadow-md' : 'border-slate-800/50 opacity-60'
                    }`}
                  >
                    <div>
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-2.5">
                          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                            <Server className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <h4 className="text-sm font-semibold text-white tracking-wide">{server.name}</h4>
                              <button 
                                onClick={() => togglePinServer(server.id)}
                                className="text-slate-500 hover:text-amber-400 transition p-0.5"
                                title="Pin Server"
                              >
                                <Star className={`w-3.5 h-3.5 ${isPinned ? 'fill-amber-400 text-amber-400' : ''}`} />
                              </button>
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase border border-slate-700">
                                {server.transport}
                              </span>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${statusBg}`}>
                                {server.enabled ? server.status : 'DISABLED'}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleHealthCheck(server)}
                            disabled={isHealthChecking || !server.enabled}
                            title="Run Health Check"
                            className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 transition"
                          >
                            <Activity className={`w-3.5 h-3.5 ${isHealthChecking ? 'animate-pulse text-indigo-400' : ''}`} />
                          </button>
                          <button
                            onClick={() => handleToggleEnable(server)}
                            title={server.enabled ? 'Disable Server' : 'Enable Server'}
                            className={`p-1.5 rounded-lg border transition ${
                              server.enabled 
                                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/40' 
                                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            <Power className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(server)}
                            title="Delete Server"
                            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-rose-950/40 border border-slate-700/60 hover:border-rose-500/40 text-slate-400 hover:text-rose-400 transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                        {server.description || 'No description provided.'}
                      </p>

                      <div className="mt-4 p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px]">
                        <span className="font-mono text-slate-400 truncate max-w-[190px]">{server.server_url}</span>
                        <span className="text-slate-500 font-mono">auth: {server.authentication_type}</span>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                      <button
                        onClick={() => handleOpenCapabilities(server)}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        <Layers className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Capabilities ({server.capabilities_count || 0})</span>
                      </button>

                      <button
                        onClick={() => handleRefreshDiscovery(server)}
                        disabled={isDiscovering || !server.enabled}
                        className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin' : ''}`} />
                        <span>{isDiscovering ? 'Discovering...' : 'Discover'}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. TOOL CATALOG */}
      {/* ========================================================================= */}
      {activeMode === 'tools' && (
        <div className="space-y-5 animate-fade-in">
          {/* Action & Filter Bar */}
          <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-3">
            <div className="flex items-center gap-2 flex-1 max-w-lg">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={toolSearchQuery}
                  onChange={(e) => setToolSearchQuery(e.target.value)}
                  placeholder="Search discovered tools across servers..."
                  className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
                />
              </div>
              <button
                onClick={() => setToolFilterPinned(!toolFilterPinned)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition ${
                  toolFilterPinned
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
                title="Filter Pinned"
              >
                <Star className={`w-3.5 h-3.5 ${toolFilterPinned ? 'fill-amber-400 text-amber-400' : ''}`} />
                <span className="hidden sm:inline">Pinned</span>
              </button>
            </div>

            {/* Risk Filters */}
            <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl gap-1 shrink-0 overflow-x-auto">
              {[
                { id: 'all', label: 'All Risk' },
                { id: 'safe', label: 'Safe', color: 'text-emerald-400' },
                { id: 'restricted', label: 'Restricted', color: 'text-amber-400' },
                { id: 'invalid', label: 'Invalid', color: 'text-rose-400' }
              ].map((rf) => (
                <button
                  key={rf.id}
                  onClick={() => setSelectedRiskFilter(rf.id)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    selectedRiskFilter === rf.id 
                      ? 'bg-indigo-600 text-white' 
                      : `text-slate-400 hover:text-white ${rf.color || ''}`
                  }`}
                >
                  {rf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tools Grid */}
          {isLoadingTools ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP tool catalog...</span>
            </div>
          ) : filteredTools.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <Wrench className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No MCP Tools Available</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Run discovery on a registered server to load tool capabilities.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredTools.map((tool) => {
                const isPinned = pinnedTools.includes(tool.id);
                const isSafe = tool.risk_level === 'safe';
                const isRestricted = tool.risk_level === 'restricted';
                const isInvalid = tool.risk_level === 'invalid';

                const riskBadge = 
                  isSafe ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                  isRestricted ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                  'bg-rose-500/10 text-rose-400 border-rose-500/20';

                return (
                  <div
                    key={tool.id}
                    className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                      tool.enabled && !tool.is_stale 
                        ? 'border-slate-800 hover:border-slate-700 shadow-md' 
                        : 'border-slate-800/40 opacity-60'
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                            <Wrench className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <h4 className="text-sm font-bold text-white font-mono">{tool.name}</h4>
                              <button 
                                onClick={() => togglePinTool(tool.id)}
                                className="text-slate-500 hover:text-amber-400 transition p-0.5"
                                title="Pin Tool"
                              >
                                <Star className={`w-3.5 h-3.5 ${isPinned ? 'fill-amber-400 text-amber-400' : ''}`} />
                              </button>
                            </div>
                            <span className="text-[10px] text-slate-400">Server: <strong className="text-slate-300">{tool.server_name}</strong></span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${riskBadge}`}>
                            {tool.risk_level}
                          </span>
                        </div>
                      </div>

                      <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                        {tool.description || 'No description provided.'}
                      </p>

                      <div className="mt-3 flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
                          {Object.keys(tool.input_schema?.properties || {}).length} params
                        </span>
                        {tool.is_stale && (
                          <span className="px-2 py-0.5 rounded bg-rose-950/40 text-rose-400 border border-rose-500/30 font-bold">
                            STALE
                          </span>
                        )}
                        {!tool.enabled && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            DISABLED
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                      <button
                        onClick={() => handleToggleToolEnable(tool)}
                        className={`p-1.5 rounded-lg border transition ${
                          tool.enabled
                            ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400'
                            : 'bg-slate-800 border-slate-700 text-slate-400'
                        }`}
                        title={tool.enabled ? 'Disable Tool' : 'Enable Tool'}
                      >
                        <Power className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleOpenToolModal(tool)}
                        className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>Inspect &amp; Run</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. RESOURCES VIEWER */}
      {/* ========================================================================= */}
      {activeMode === 'resources' && (
        <div className="space-y-5 animate-fade-in">
          <div className="relative max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={resourceSearchQuery}
              onChange={(e) => setResourceSearchQuery(e.target.value)}
              placeholder="Search discovered workspace resources..."
              className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
            />
          </div>

          {isLoadingResources ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP resources...</span>
            </div>
          ) : resources.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <FileCode className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No MCP Resources Discovered</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Connect servers that expose static or dynamic read-only resources.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {resources.map((res) => (
                <div key={res.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition shadow-sm">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                        <FileCode className="w-4 h-4" />
                      </div>
                      <div className="overflow-hidden">
                        <h4 className="text-sm font-bold text-white font-mono truncate">{res.name}</h4>
                        <span className="text-[10px] text-slate-400">Server: {res.server_name}</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                      {res.description || 'No description provided.'}
                    </p>

                    <div className="mt-3 p-2 bg-slate-950 border border-slate-800 rounded-xl text-[10px] font-mono text-indigo-400 truncate">
                      {res.uri}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={() => handleOpenResource(res)}
                      className="px-3.5 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Read Resource</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 5. PROMPTS HUB */}
      {/* ========================================================================= */}
      {activeMode === 'prompts' && (
        <div className="space-y-5 animate-fade-in">
          <div className="relative max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={promptSearchQuery}
              onChange={(e) => setPromptSearchQuery(e.target.value)}
              placeholder="Search parameterized prompt templates..."
              className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
            />
          </div>

          {isLoadingPrompts ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP prompt templates...</span>
            </div>
          ) : prompts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <MessageSquare className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No Prompt Templates Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Discovered prompts can be rendered safely and inspected as untrusted context.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {prompts.map((p) => (
                <div key={p.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition shadow-sm">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-white font-mono">{p.name}</h4>
                        <span className="text-[10px] text-slate-400">Server: {p.server_name}</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                      {p.description || 'No description provided.'}
                    </p>

                    <div className="mt-3 flex items-center gap-1.5 flex-wrap">
                      {(p.arguments || []).map(arg => (
                        <span key={arg.name} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[10px] font-mono text-slate-300">
                          {arg.name}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={() => handleOpenPrompt(p)}
                      className="px-3.5 py-1.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Sliders className="w-3.5 h-3.5" />
                      <span>Render Template</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 6. SECURITY & RBAC DASHBOARD */}
      {/* ========================================================================= */}
      {activeMode === 'security' && (
        <div className="space-y-6 animate-fade-in">
          {isLoadingSecurity ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP security configuration...</span>
            </div>
          ) : (
            <>
              {/* Security Boundary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Trust Boundary</span>
                  <div className="flex items-center gap-2 mt-1">
                    <Shield className="w-4 h-4 text-indigo-400" />
                    <span className="font-mono text-sm font-bold text-white">{securityStatus?.trust_label_policy || 'UNTRUSTED_MCP'}</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Strict untrusted isolation on all external MCP responses.</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Confirmation Gate</span>
                  <div className="flex items-center gap-2 mt-1">
                    <Lock className="w-4 h-4 text-amber-400" />
                    <span className="font-mono text-sm font-bold text-white">ACTIVE (HMAC-SHA256)</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Single-use cryptographically signed tokens for restricted operations.</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">SSRF Defense</span>
                  <div className="flex items-center gap-2 mt-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-mono text-sm font-bold text-white">ENFORCED</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Loopback, private subnet, and AWS metadata endpoint blocking.</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Tenant Boundary</span>
                  <div className="flex items-center gap-2 mt-1">
                    <Layers className="w-4 h-4 text-purple-400" />
                    <span className="font-mono text-sm font-bold text-white">WORKSPACE ISOLATED</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Zero cross-tenant capability execution or resource leakage.</p>
                </div>
              </div>

              {/* Active RBAC Permissions Matrix */}
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white">Active Capability RBAC Permissions</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Permissions evaluated dynamically against the backend authority.</p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-mono font-bold">
                    Role: {securityStatus?.user_role || 'user'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                  {(securityStatus?.active_permissions || [
                    'mcp:server:view', 'mcp:server:manage',
                    'mcp:tool:view', 'mcp:tool:execute', 'mcp:tool:manage',
                    'mcp:resource:view', 'mcp:resource:read', 'mcp:resource:manage',
                    'mcp:prompt:view', 'mcp:prompt:render', 'mcp:prompt:manage'
                  ]).map((perm) => (
                    <div key={perm} className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2">
                      <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span className="text-xs font-mono text-slate-200 truncate">{perm}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 7. EXECUTION HISTORY */}
      {/* ========================================================================= */}
      {activeMode === 'history' && (
        <div className="space-y-5 animate-fade-in">
          {/* Filter Bar */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-semibold">Filter Status:</span>
              <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl gap-1">
                {['all', 'COMPLETED', 'FAILED', 'REQUIRES_CONFIRMATION'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setHistoryStatusFilter(st)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                      historyStatusFilter === st
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={fetchExecutionHistory}
              className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white rounded-xl text-xs flex items-center gap-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh History</span>
            </button>
          </div>

          {/* History Table */}
          {isLoadingHistory ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading execution trace log...</span>
            </div>
          ) : executionHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <History className="w-8 h-8 text-slate-500 mb-2" />
              <h3 className="text-sm font-semibold text-slate-200">No Executions Recorded</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Tools executed manually or via multi-agent pipelines will be listed here.</p>
            </div>
          ) : (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Started</th>
                      <th className="py-3 px-4">Tool / Capability</th>
                      <th className="py-3 px-4">Execution ID</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {executionHistory.map((ex) => {
                      const isOk = ex.status === 'COMPLETED' || ex.status === 'SUCCESS';
                      const isFailed = ex.status === 'FAILED';
                      const statusClass = isOk 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : isFailed 
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20';

                      return (
                        <tr key={ex.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                            {ex.started_at ? new Date(ex.started_at).toLocaleString() : '---'}
                          </td>
                          <td className="py-3 px-4 font-bold text-white">
                            {ex.tool_name || ex.tool_id}
                          </td>
                          <td className="py-3 px-4 text-slate-400 text-[11px]">
                            {ex.execution_id.slice(0, 8)}...
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${statusClass}`}>
                              {ex.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-slate-300">
                            {ex.duration_ms ? `${Math.round(ex.duration_ms)}ms` : '---'}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => {
                                setSelectedExecution(ex);
                                setShowExecutionDetailModal(true);
                              }}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-semibold transition"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 8. SECURITY AUDIT LOG */}
      {/* ========================================================================= */}
      {activeMode === 'audit' && (
        <div className="space-y-5 animate-fade-in">
          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={auditSearchQuery}
                onChange={(e) => setAuditSearchQuery(e.target.value)}
                placeholder="Search audit log by operation, reason..."
                className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
              />
            </div>

            <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl gap-1 shrink-0">
              {['all', 'ALLOW', 'REQUIRE_CONFIRMATION', 'DENY'].map((dec) => (
                <button
                  key={dec}
                  onClick={() => setAuditDecisionFilter(dec)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    auditDecisionFilter === dec
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {dec}
                </button>
              ))}
            </div>
          </div>

          {/* Audit Events Table */}
          {isLoadingSecurity ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading audit events...</span>
            </div>
          ) : filteredAuditLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <Shield className="w-8 h-8 text-slate-500 mb-2" />
              <h3 className="text-sm font-semibold text-slate-200">No Security Events Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Audit log records all security evaluations with redacted metadata.</p>
            </div>
          ) : (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Operation</th>
                      <th className="py-3 px-4">Decision</th>
                      <th className="py-3 px-4">Reason Code</th>
                      <th className="py-3 px-4">Capability</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {filteredAuditLogs.map((ev) => {
                      const isAllow = ev.decision === 'ALLOW';
                      const isDeny = ev.decision === 'DENY';
                      const decClass = isAllow 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : isDeny 
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20';

                      return (
                        <tr key={ev.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '---'}
                          </td>
                          <td className="py-3 px-4 font-bold text-white">
                            {ev.operation}
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${decClass}`}>
                              {ev.decision}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-indigo-400 font-semibold">
                            {ev.reason_code}
                          </td>
                          <td className="py-3 px-4 text-slate-400 text-[11px] truncate max-w-[200px]">
                            {ev.capability_id || '---'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SERVER REGISTRATION MODAL */}
      {/* ========================================================================= */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Server className="w-5 h-5 text-indigo-400" />
                Register Model Context Protocol Server
              </h3>
              <button onClick={() => setShowRegisterModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Server Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., github-server, filesystem-daemon"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:border-indigo-500 outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Connection URL / Command *</label>
                <input
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="e.g., http://localhost:8080/sse or stdio:///usr/bin/mcp"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white font-mono focus:border-indigo-500 outline-none transition"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Transport</label>
                  <select
                    value={transport}
                    onChange={(e) => setTransport(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                  >
                    <option value="sse">Server-Sent Events (SSE)</option>
                    <option value="streamable_http">Streamable HTTP</option>
                    <option value="stdio">Standard I/O (stdio)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Authentication</label>
                  <select
                    value={authType}
                    onChange={(e) => setAuthType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                  >
                    <option value="none">None / Public</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="api_key">API Key</option>
                    <option value="oauth">OAuth 2.0</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Description (Optional)</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe tools provided by this server..."
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:border-indigo-500 outline-none transition"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5"
                >
                  {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  <span>Register Server</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* CAPABILITIES INSPECTOR MODAL */}
      {/* ========================================================================= */}
      {showCapabilitiesModal && selectedServer && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-400" />
                  {selectedServer.name} &mdash; Discovered Capabilities
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">{selectedServer.server_url}</p>
              </div>
              <button onClick={() => setShowCapabilitiesModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Capability Tab Filters */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center bg-slate-950 border border-slate-800 p-1 rounded-xl gap-1">
                {['tool', 'resource', 'prompt'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveCapTab(t)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold uppercase transition ${
                      activeCapTab === t ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {t}s ({capabilities.filter(c => c.capability_type === t).length})
                  </button>
                ))}
              </div>

              <input
                type="text"
                value={capSearch}
                onChange={(e) => setCapSearch(e.target.value)}
                placeholder="Filter capabilities..."
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 outline-none w-56"
              />
            </div>

            {/* Capabilities List & Detail Split */}
            <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="overflow-y-auto space-y-2 pr-1 max-h-[50vh]">
                {capabilities
                  .filter(c => c.capability_type === activeCapTab && (!capSearch || c.name.toLowerCase().includes(capSearch.toLowerCase())))
                  .map((cap) => (
                    <div
                      key={cap.id}
                      onClick={() => setSelectedCap(cap)}
                      className={`p-3 rounded-xl border transition cursor-pointer ${
                        selectedCap?.id === cap.id 
                          ? 'bg-indigo-950/40 border-indigo-500/50' 
                          : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-white">{cap.name}</span>
                        <span className="text-[10px] font-mono text-slate-500">v{cap.version}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{cap.description || 'No description'}</p>
                    </div>
                  ))}
              </div>

              {/* JSON Schema Viewer */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-y-auto max-h-[50vh]">
                {selectedCap ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <span className="font-mono text-xs font-bold text-indigo-300">{selectedCap.name}</span>
                      <span className="text-[10px] font-mono text-slate-400">{selectedCap.capability_type}</span>
                    </div>
                    <pre className="text-[11px] font-mono text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(selectedCap.input_schema || selectedCap.metadata || {}, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs">
                    Select a capability to inspect its schema and metadata
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-slate-800 pt-3 flex justify-end">
              <button
                onClick={() => setShowCapabilitiesModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TOOL INSPECT & RUN MODAL */}
      {/* ========================================================================= */}
      {showToolModal && selectedTool && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Wrench className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono">{selectedTool.name}</h3>
                  <p className="text-xs text-slate-400">Server: <strong className="text-slate-200">{selectedTool.server_name}</strong></p>
                </div>
              </div>
              <button onClick={() => setShowToolModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex items-center bg-slate-950 border border-slate-800 p-1 rounded-xl gap-1">
              <button
                onClick={() => setToolModalTab('schema')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  toolModalTab === 'schema' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Schema Inspector
              </button>
              <button
                onClick={() => setToolModalTab('execute')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  toolModalTab === 'execute' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Execute Tool
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {toolModalTab === 'schema' && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">{selectedTool.description || 'No description provided.'}</p>
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">JSON Schema</span>
                    <pre className="text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(selectedTool.input_schema || {}, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {toolModalTab === 'execute' && (
                <div className="space-y-4">
                  {/* Risk & Confirmation Banner */}
                  {selectedTool.risk_level === 'restricted' && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-2">
                      <div className="flex items-center gap-2 font-bold text-amber-400">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Restricted Operation &mdash; Confirmation Required</span>
                      </div>
                      <p className="leading-relaxed">
                        This tool may modify external state, access sensitive resources, or execute write actions.
                      </p>
                      <label className="flex items-center gap-2 mt-2 cursor-pointer font-semibold text-white">
                        <input
                          type="checkbox"
                          checked={restrictedConfirmed}
                          onChange={(e) => setRestrictedConfirmed(e.target.checked)}
                          className="rounded border-amber-500 text-indigo-600 focus:ring-0"
                        />
                        <span>I understand and authorize execution of this tool</span>
                      </label>
                    </div>
                  )}

                  {/* Arguments Form */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-slate-300">Tool Parameters</h4>
                    {Object.keys(selectedTool.input_schema?.properties || {}).length === 0 ? (
                      <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-500 text-xs">
                        This tool requires no input arguments.
                      </div>
                    ) : (
                      Object.keys(selectedTool.input_schema?.properties || {}).map((paramKey) => {
                        const prop = selectedTool.input_schema.properties[paramKey];
                        return (
                          <div key={paramKey} className="space-y-1">
                            <label className="text-xs font-mono text-slate-300 flex items-center justify-between">
                              <span>{paramKey}</span>
                              <span className="text-[10px] text-slate-500">{prop.type || 'any'}</span>
                            </label>
                            <input
                              type="text"
                              value={executionArgs[paramKey] !== undefined ? executionArgs[paramKey] : ''}
                              onChange={(e) => setExecutionArgs({ ...executionArgs, [paramKey]: e.target.value })}
                              placeholder={prop.description || paramKey}
                              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-indigo-500 outline-none"
                            />
                          </div>
                        );
                      })
                    )}
                  </div>

                  {/* Execution Error Banner */}
                  {executionError && (
                    <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                      <span className="font-mono">{executionError}</span>
                    </div>
                  )}

                  {/* Sanitized Result Display */}
                  {executionResult && (
                    <div className="space-y-2 pt-2 border-t border-slate-800">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                          <span>Sanitized Result ({executionResult.duration_ms}ms)</span>
                        </span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(executionResult.result, null, 2));
                            setCopiedResult(true);
                            setTimeout(() => setCopiedResult(false), 2000);
                          }}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-semibold flex items-center gap-1 transition"
                        >
                          {copiedResult ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedResult ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>

                      <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto max-h-56 whitespace-pre-wrap">
                        {JSON.stringify(executionResult.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-slate-800 pt-3 flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500">Trust Label: UNTRUSTED_MCP</span>
              <div className="flex items-center gap-2">
                {toolModalTab === 'execute' && (
                  <button
                    onClick={handleExecuteTool}
                    disabled={isExecuting || !selectedTool.available_for_execution}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                  >
                    {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                    <span>{isExecuting ? 'Executing...' : 'Run Execution'}</span>
                  </button>
                )}
                <button
                  onClick={() => setShowToolModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* RESOURCE VIEWER MODAL */}
      {/* ========================================================================= */}
      {showResourceModal && selectedResource && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <FileCode className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono">{selectedResource.name}</h3>
                  <p className="text-xs text-slate-400 font-mono">{selectedResource.uri}</p>
                </div>
              </div>
              <button onClick={() => setShowResourceModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {isReadingResource ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-xs gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
                  <span>Reading resource content from MCP server...</span>
                </div>
              ) : resourceReadError ? (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1 font-mono">
                  <span className="font-bold block">Read Error:</span>
                  <p>{resourceReadError}</p>
                </div>
              ) : resourceContent ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">Sanitized Content Preview</span>
                    <span className="text-[10px] font-mono text-slate-400">{resourceContent.size} bytes</span>
                  </div>
                  <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto max-h-72 whitespace-pre-wrap">
                    {resourceContent.text}
                  </pre>
                </div>
              ) : null}
            </div>

            <div className="border-t border-slate-800 pt-3 flex justify-end">
              <button
                onClick={() => setShowResourceModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PROMPT RENDERER MODAL */}
      {/* ========================================================================= */}
      {showPromptModal && selectedPrompt && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono">{selectedPrompt.name}</h3>
                  <p className="text-xs text-slate-400">Server: {selectedPrompt.server_name}</p>
                </div>
              </div>
              <button onClick={() => setShowPromptModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              <p className="text-xs text-slate-400 leading-relaxed">{selectedPrompt.description || 'No description provided.'}</p>

              {/* Arguments Entry Form */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-300">Template Arguments</h4>
                {(selectedPrompt.arguments || []).map((arg) => (
                  <div key={arg.name} className="space-y-1">
                    <label className="text-xs font-mono text-slate-300">{arg.name}</label>
                    <input
                      type="text"
                      value={promptArgs[arg.name] || ''}
                      onChange={(e) => setPromptArgs({ ...promptArgs, [arg.name]: e.target.value })}
                      placeholder={arg.description || arg.name}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:border-purple-500 outline-none"
                    />
                  </div>
                ))}
              </div>

              {promptRenderError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono">
                  {promptRenderError}
                </div>
              )}

              {renderedPrompt && (
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <span className="text-xs font-semibold text-slate-300">Rendered Template Messages</span>
                  <div className="space-y-2">
                    {renderedPrompt.messages.map((msg, idx) => (
                      <div key={idx} className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] font-bold font-mono text-purple-400 uppercase">{msg.role}</span>
                        <p className="text-xs text-slate-200 whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-slate-800 pt-3 flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-500">Isolation: UNTRUSTED_MCP</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRenderPrompt}
                  disabled={isRenderingPrompt}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5"
                >
                  {isRenderingPrompt ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  <span>Render Template</span>
                </button>
                <button
                  onClick={() => setShowPromptModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* EXECUTION DETAIL INSPECTOR MODAL */}
      {/* ========================================================================= */}
      {showExecutionDetailModal && selectedExecution && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                <History className="w-5 h-5 text-indigo-400" />
                Execution Trace &mdash; {selectedExecution.tool_name || selectedExecution.tool_id}
              </h3>
              <button onClick={() => setShowExecutionDetailModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs">
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Execution ID</span>
                  <span className="text-slate-200">{selectedExecution.execution_id}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Status</span>
                  <span className="text-emerald-400 font-bold">{selectedExecution.status}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Started At</span>
                  <span className="text-slate-300">{selectedExecution.started_at ? new Date(selectedExecution.started_at).toLocaleString() : '---'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Duration</span>
                  <span className="text-slate-300">{selectedExecution.duration_ms ? `${Math.round(selectedExecution.duration_ms)}ms` : '---'}</span>
                </div>
              </div>

              {selectedExecution.error && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 space-y-1">
                  <span className="font-bold block">Execution Failure:</span>
                  <p>{selectedExecution.error}</p>
                </div>
              )}

              {selectedExecution.result_preview && (
                <div className="space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Sanitized Output Payload</span>
                  <pre className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 overflow-x-auto whitespace-pre-wrap max-h-60">
                    {selectedExecution.result_preview}
                  </pre>
                </div>
              )}
            </div>

            <div className="border-t border-slate-800 pt-3 flex justify-end">
              <button
                onClick={() => setShowExecutionDetailModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
