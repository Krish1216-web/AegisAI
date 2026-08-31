import React, { useState, useEffect } from 'react';
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
  Clock
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
  getMCPSecurityAuditLog
} from '../../api/mcp';

export default function UserMcpMarket({ triggerNotification }) {
  // Top Level Mode: 'servers' | 'tools' | 'resources' | 'prompts' | 'security'
  const [activeMode, setActiveMode] = useState('servers');

  // Security & Audit State (Phase 6.6)
  const [securityStatus, setSecurityStatus] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isLoadingSecurity, setIsLoadingSecurity] = useState(false);

  // Servers State
  const [servers, setServers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  
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
  const [activeTab, setActiveTab] = useState('tool');
  const [capSearch, setCapSearch] = useState('');
  const [isLoadingCaps, setIsLoadingCaps] = useState(false);
  const [selectedCap, setSelectedCap] = useState(null);

  // Discovery Summary Modal
  const [discoverySummary, setDiscoverySummary] = useState(null);

  // Tool Catalog & Execution State (Phase 6.3 & 6.4)
  const [tools, setTools] = useState([]);
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [toolSearchQuery, setToolSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('all');
  const [selectedTool, setSelectedTool] = useState(null);
  const [showToolModal, setShowToolModal] = useState(false);
  const [toolModalTab, setToolModalTab] = useState('schema'); // 'schema' | 'execute'
  const [executionArgs, setExecutionArgs] = useState({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [executionError, setExecutionError] = useState(null);
  const [restrictedConfirmed, setRestrictedConfirmed] = useState(false);

  // In-flight state trackers
  const [discoveringIds, setDiscoveringIds] = useState(new Set());
  const [healthCheckingIds, setHealthCheckingIds] = useState(new Set());
  const [healthMetrics, setHealthMetrics] = useState({});

  // Resources State (Phase 6.5)
  const [resources, setResources] = useState([]);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [resourceSearchQuery, setResourceSearchQuery] = useState('');
  const [selectedResource, setSelectedResource] = useState(null);
  const [showResourceModal, setShowResourceModal] = useState(false);
  const [isReadingResource, setIsReadingResource] = useState(false);
  const [resourceContent, setResourceContent] = useState(null);
  const [resourceReadError, setResourceReadError] = useState(null);

  // Prompts State (Phase 6.5)
  const [prompts, setPrompts] = useState([]);
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(false);
  const [promptSearchQuery, setPromptSearchQuery] = useState('');
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [isRenderingPrompt, setIsRenderingPrompt] = useState(false);
  const [promptArgs, setPromptArgs] = useState({});
  const [renderedPrompt, setRenderedPrompt] = useState(null);
  const [promptRenderError, setPromptRenderError] = useState(null);

  const fetchServers = async () => {
    setIsLoading(true);
    try {
      const data = await listMCPServers();
      setServers(data.servers || []);
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
      triggerNotification?.('Error', 'Failed to load MCP servers from server.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTools = async () => {
    setIsLoadingTools(true);
    try {
      if (toolSearchQuery.trim()) {
        const data = await searchWorkspaceTools({
          query: toolSearchQuery.trim(),
          risk_level: selectedRiskFilter !== 'all' ? selectedRiskFilter : undefined,
          enabled_only: false,
          include_stale: true,
          limit: 50
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
      console.error('Failed to load tool catalog:', err);
      triggerNotification?.('Error', 'Failed to load tools catalog.');
    } finally {
      setIsLoadingTools(false);
    }
  };

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

  const fetchSecurityData = async () => {
    setIsLoadingSecurity(true);
    try {
      const [statusRes, auditRes] = await Promise.all([
        getMCPSecurityStatus(),
        getMCPSecurityAuditLog(50)
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

  useEffect(() => {
    fetchServers();
  }, []);

  useEffect(() => {
    if (activeMode === 'tools') {
      const timer = setTimeout(() => {
        fetchTools();
      }, 250);
      return () => clearTimeout(timer);
    } else if (activeMode === 'resources') {
      const timer = setTimeout(() => {
        fetchResources();
      }, 250);
      return () => clearTimeout(timer);
    } else if (activeMode === 'prompts') {
      const timer = setTimeout(() => {
        fetchPrompts();
      }, 250);
      return () => clearTimeout(timer);
    } else if (activeMode === 'security') {
      fetchSecurityData();
    }
  }, [activeMode, toolSearchQuery, selectedRiskFilter, resourceSearchQuery, promptSearchQuery]);

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
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to toggle server state.');
    }
  };

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

  const handleDelete = async (server) => {
    if (!window.confirm(`Are you sure you want to delete MCP server '${server.name}'?`)) return;
    try {
      await deleteMCPServer(server.id);
      triggerNotification?.('Deleted', `Removed MCP server '${server.name}'`);
      fetchServers();
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
    } catch (err) {
      triggerNotification?.('Health Check Error', err.message || 'Failed to complete health check.');
    } finally {
      setHealthCheckingIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const handleRefreshDiscovery = async (server, force = true) => {
    setDiscoveringIds(prev => new Set(prev).add(server.id));
    try {
      const res = await refreshServerDiscovery(server.id, force);
      setDiscoverySummary(res);
      triggerNotification?.(
        'Discovery Refreshed', 
        `Synchronized ${res.total_tools} tools (+${res.tools_added}, ~${res.tools_changed}), ${res.total_resources} resources, ${res.total_prompts} prompts.`
      );
      fetchServers();
    } catch (err) {
      triggerNotification?.('Discovery Failed', err.message || 'Failed to discover capabilities.');
    } finally {
      setDiscoveringIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const handleViewCapabilities = async (server) => {
    setSelectedServer(server);
    setShowCapabilitiesModal(true);
    setIsLoadingCaps(true);
    setSelectedCap(null);
    setCapSearch('');
    try {
      const res = await listServerCapabilities(server.id, undefined, undefined, true);
      setCapabilities(res.capabilities || []);
    } catch (err) {
      triggerNotification?.('Error', err.message || 'Failed to load capabilities.');
    } finally {
      setIsLoadingCaps(false);
    }
  };

  // Phase 6.4: Tool Execution Handler
  const handleExecute = async () => {
    if (!selectedTool) return;
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);

    try {
      let confirmationToken = undefined;
      if (selectedTool.risk_level === 'restricted') {
        const confRes = await generateToolConfirmationToken(selectedTool.id, executionArgs);
        confirmationToken = confRes.token;
      }

      const res = await executeMCPTool(selectedTool.id, {
        arguments: executionArgs,
        confirmation_token: confirmationToken,
        timeout: 20.0
      });
      setExecutionResult(res);
      triggerNotification?.('Tool Executed', `Executed '${selectedTool.name}' in ${res.duration_ms}ms`);
    } catch (err) {
      setExecutionError(err.message || 'Tool execution failed');
      triggerNotification?.('Execution Failed', err.message || 'Tool execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleReadResource = async (resource) => {
    setSelectedResource(resource);
    setShowResourceModal(true);
    setIsReadingResource(true);
    setResourceReadError(null);
    setResourceContent(null);

    try {
      const res = await readMCPResource(resource.id);
      setResourceContent(res);
      triggerNotification?.('Resource Loaded', `Successfully read '${resource.name}'`);
    } catch (err) {
      setResourceReadError(err.message || 'Failed to read resource content');
      triggerNotification?.('Read Failed', err.message || 'Failed to read resource');
    } finally {
      setIsReadingResource(false);
    }
  };

  const handleOpenPrompt = (prompt) => {
    setSelectedPrompt(prompt);
    setShowPromptModal(true);
    setPromptRenderError(null);
    setRenderedPrompt(null);
    const initial = {};
    (prompt.arguments || []).forEach(arg => {
      initial[arg.name] = '';
    });
    setPromptArgs(initial);
  };

  const handleRenderPrompt = async () => {
    if (!selectedPrompt) return;
    setIsRenderingPrompt(true);
    setPromptRenderError(null);
    setRenderedPrompt(null);

    try {
      const res = await renderMCPPrompt(selectedPrompt.id, promptArgs);
      setRenderedPrompt(res);
      triggerNotification?.('Prompt Rendered', `Rendered '${selectedPrompt.name}' template.`);
    } catch (err) {
      setPromptRenderError(err.message || 'Failed to render prompt template');
      triggerNotification?.('Render Failed', err.message || 'Failed to render prompt');
    } finally {
      setIsRenderingPrompt(false);
    }
  };

  const filteredServers = servers.filter(item => 
    item.name.toLowerCase().includes(search.toLowerCase()) || 
    item.server_url.toLowerCase().includes(search.toLowerCase()) ||
    item.transport.toLowerCase().includes(search.toLowerCase())
  );

  const filterCapabilities = (list) => {
    if (!capSearch.trim()) return list;
    const term = capSearch.toLowerCase();
    return list.filter(c => c.name.toLowerCase().includes(term) || (c.description && c.description.toLowerCase().includes(term)));
  };

  const toolsList = filterCapabilities(capabilities.filter(c => c.capability_type === 'tool'));
  const resourcesList = filterCapabilities(capabilities.filter(c => c.capability_type === 'resource'));
  const promptsList = filterCapabilities(capabilities.filter(c => c.capability_type === 'prompt'));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Server className="w-5 h-5 text-indigo-400" />
            Model Context Protocol (MCP) Ecosystem
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Manage external tool server connections, discover dynamic tools, inspect JSON Schemas, read secure resources, and render prompt templates.
          </p>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveMode('servers')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeMode === 'servers'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>Servers ({servers.length})</span>
          </button>
          <button
            onClick={() => setActiveMode('tools')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeMode === 'tools'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Tools</span>
          </button>
          <button
            onClick={() => setActiveMode('resources')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeMode === 'resources'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>Resources</span>
          </button>
          <button
            onClick={() => setActiveMode('prompts')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeMode === 'prompts'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Prompts</span>
          </button>
          <button
            onClick={() => setActiveMode('security')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              activeMode === 'security'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Security & Audit</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* VIEW MODE 1: SERVERS REGISTRY */}
      {/* ========================================================================= */}
      {activeMode === 'servers' && (
        <>
          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search registered servers..."
                className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
              />
            </div>

            <button
              onClick={() => setShowRegisterModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>Add MCP Server</span>
            </button>
          </div>

          {/* Stats Overview */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Registered Servers', value: servers.length.toString(), color: 'text-white' },
              { label: 'Healthy & Active', value: servers.filter(s => s.status === 'active' && s.enabled).length.toString(), color: 'text-emerald-400' },
              { label: 'SSE / HTTP Links', value: servers.filter(s => s.transport !== 'stdio').length.toString(), color: 'text-indigo-400' },
              { label: 'Active Capabilities', value: servers.reduce((acc, s) => acc + (s.capabilities_count || 0), 0).toString(), color: 'text-purple-400' }
            ].map((stat, idx) => (
              <div key={idx} className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col gap-1 backdrop-blur-sm">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">{stat.label}</span>
                <span className={`text-2xl font-bold font-mono mt-1 ${stat.color}`}>{stat.value}</span>
              </div>
            ))}
          </div>

          {/* Server Cards Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP server registry...</span>
            </div>
          ) : filteredServers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <Server className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No MCP Servers Registered</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Register an MCP server to discover dynamic tools and capabilities.</p>
              <button
                onClick={() => setShowRegisterModal(true)}
                className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Register First Server</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredServers.map((server) => {
                const isDiscovering = discoveringIds.has(server.id);
                const isHealthChecking = healthCheckingIds.has(server.id);
                const health = healthMetrics[server.id];

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
                            <h4 className="text-sm font-semibold text-white tracking-wide">{server.name}</h4>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase border border-slate-700">
                                {server.transport}
                              </span>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${statusBg}`}>
                                {server.enabled ? server.status : 'DISABLED'}
                              </span>
                              {server.server_version && (
                                <span className="text-[9px] font-mono text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                                  v{server.server_version}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleHealthCheck(server)}
                            disabled={isHealthChecking || !server.enabled}
                            title="Run Health Ping"
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

                      <div className="mt-3 p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] font-mono text-slate-400 truncate">
                        {server.server_url}
                      </div>

                      {health && (
                        <div className="mt-2 text-[10px] flex items-center justify-between text-slate-400 px-1">
                          <span>Latency: <strong className="text-slate-200 font-mono">{health.latency_ms ? `${health.latency_ms}ms` : 'N/A'}</strong></span>
                          <span>Health: <strong className={health.is_healthy ? 'text-emerald-400' : 'text-rose-400'}>{health.is_healthy ? 'ONLINE' : 'ERROR'}</strong></span>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                      <div className="text-[11px] text-slate-400">
                        <span className="font-semibold text-indigo-300">{server.capabilities_count || 0}</span> active capabilities
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleRefreshDiscovery(server, true)}
                          disabled={isDiscovering || !server.enabled}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/80 disabled:opacity-50 text-slate-200 text-xs font-medium rounded-lg flex items-center gap-1.5 transition"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin text-indigo-400' : ''}`} />
                          <span>{isDiscovering ? 'Refreshing...' : 'Refresh'}</span>
                        </button>
                        <button
                          onClick={() => handleViewCapabilities(server)}
                          className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-medium rounded-lg flex items-center gap-1 transition"
                        >
                          <span>Capabilities</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 2: DEDICATED TOOL CATALOG & EXECUTION (PHASE 6.3 & 6.4) */}
      {/* ========================================================================= */}
      {activeMode === 'tools' && (
        <div className="space-y-4">
          
          {/* Tool Search & Risk Filters */}
          <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={toolSearchQuery}
                onChange={(e) => setToolSearchQuery(e.target.value)}
                placeholder="Search tools by name, description, or intent..."
                className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition font-sans"
              />
            </div>

            {/* Risk Filters */}
            <div className="flex items-center gap-1.5 bg-slate-900/80 border border-slate-800 p-1 rounded-xl text-xs">
              {[
                { id: 'all', label: 'All Risks' },
                { id: 'safe', label: 'Safe', color: 'text-emerald-400' },
                { id: 'restricted', label: 'Restricted', color: 'text-amber-400' },
                { id: 'invalid', label: 'Invalid', color: 'text-rose-400' }
              ].map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => setSelectedRiskFilter(filter.id)}
                  className={`px-3 py-1 rounded-lg font-medium transition ${
                    selectedRiskFilter === filter.id
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className={filter.color || ''}>{filter.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Tools Grid */}
          {isLoadingTools ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Scanning workspace tool catalog...</span>
            </div>
          ) : tools.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <Wrench className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No Discovered Tools Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Make sure your registered MCP servers are connected and discovery has been run.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {tools.map((tool) => {
                const isSafe = tool.risk_level === 'safe';
                const isRestricted = tool.risk_level === 'restricted';
                
                const riskBadge = isSafe 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                  : isRestricted 
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' 
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-400';

                return (
                  <div
                    key={tool.id}
                    className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition ${
                      tool.enabled ? 'border-slate-800 hover:border-slate-700' : 'border-slate-800/40 opacity-60'
                    }`}
                  >
                    <div>
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-white font-mono">{tool.name}</span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase ${riskBadge}`}>
                              {tool.risk_level}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-500 font-mono block mt-0.5">
                            via {tool.server_name} ({tool.server_transport})
                          </span>
                        </div>

                        <button
                          onClick={() => handleToggleToolEnable(tool)}
                          title={tool.enabled ? 'Disable Tool' : 'Enable Tool'}
                          className={`p-1.5 rounded-lg border transition ${
                            tool.enabled
                              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/40'
                              : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                        {tool.description || 'No tool description provided.'}
                      </p>

                      {/* Execution Readiness Badge */}
                      <div className="mt-3 flex items-center gap-1.5 text-[11px]">
                        {tool.available_for_execution ? (
                          <span className="text-emerald-400 flex items-center gap-1 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Execution
                          </span>
                        ) : (
                          <span className="text-slate-500 flex items-center gap-1 font-medium">
                            <XCircle className="w-3.5 h-3.5 text-rose-500" /> Unavailable ({!tool.server_enabled ? 'Server Disabled' : tool.is_stale ? 'Stale' : !tool.enabled ? 'Disabled' : 'Invalid'})
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[10px] text-slate-500 font-mono">
                        v{tool.version || 1} • {tool.input_schema?.properties ? Object.keys(tool.input_schema.properties).length : 0} params
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setSelectedTool(tool);
                            setToolModalTab('schema');
                            setShowToolModal(true);
                            setExecutionArgs({});
                            setExecutionResult(null);
                            setExecutionError(null);
                            setRestrictedConfirmed(false);
                          }}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-slate-300 text-xs font-medium rounded-lg flex items-center gap-1 transition"
                        >
                          <Code className="w-3 h-3" />
                          <span>Schema</span>
                        </button>

                        <button
                          onClick={() => {
                            setSelectedTool(tool);
                            setToolModalTab('execute');
                            setShowToolModal(true);
                            setExecutionArgs({});
                            setExecutionResult(null);
                            setExecutionError(null);
                            setRestrictedConfirmed(false);
                          }}
                          disabled={!tool.available_for_execution}
                          className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-medium rounded-lg flex items-center gap-1 transition"
                        >
                          <Play className="w-3 h-3" />
                          <span>Execute</span>
                        </button>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          )}

        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 3: RESOURCES CATALOG (PHASE 6.5) */}
      {/* ========================================================================= */}
      {activeMode === 'resources' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={resourceSearchQuery}
                onChange={(e) => setResourceSearchQuery(e.target.value)}
                placeholder="Search resources by name or URI..."
                className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
              />
            </div>
            <button
              onClick={fetchResources}
              disabled={isLoadingResources}
              className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingResources ? 'animate-spin text-indigo-400' : ''}`} />
              <span>Refresh Resources</span>
            </button>
          </div>

          {isLoadingResources ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading MCP resources catalog...</span>
            </div>
          ) : resources.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-800 rounded-2xl p-6 text-center">
              <div className="p-3 bg-slate-900 rounded-full text-slate-500 mb-3">
                <FileCode className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">No MCP Resources Discovered</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Discovered resources exposed by connected MCP servers will appear here.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {resources.map((resource) => (
                <div
                  key={resource.id}
                  className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                    resource.enabled && !resource.is_stale ? 'border-slate-800 hover:border-slate-700 shadow-md' : 'border-slate-800/40 opacity-60'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
                          <FileCode className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-white tracking-wide">{resource.name}</h4>
                          <span className="text-[10px] text-slate-400 font-mono block truncate max-w-[200px]">{resource.uri}</span>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-300 uppercase border border-slate-700">
                        {resource.mime_type || 'text/plain'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {resource.description || 'No description provided.'}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 font-mono">{resource.server_name}</span>
                    <button
                      onClick={() => handleReadResource(resource)}
                      className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition"
                    >
                      <span>Read Resource</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 4: PROMPTS CATALOG (PHASE 6.5) */}
      {/* ========================================================================= */}
      {activeMode === 'prompts' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={promptSearchQuery}
                onChange={(e) => setPromptSearchQuery(e.target.value)}
                placeholder="Search prompt templates..."
                className="bg-slate-900 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-xs text-slate-300 w-full outline-none focus:border-indigo-500 transition"
              />
            </div>
            <button
              onClick={fetchPrompts}
              disabled={isLoadingPrompts}
              className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingPrompts ? 'animate-spin text-indigo-400' : ''}`} />
              <span>Refresh Prompts</span>
            </button>
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
              <h3 className="text-sm font-semibold text-slate-200">No Prompt Templates Discovered</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">Prompt templates exposed by connected MCP servers will appear here.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {prompts.map((prompt) => (
                <div
                  key={prompt.id}
                  className={`bg-slate-900/80 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                    prompt.enabled && !prompt.is_stale ? 'border-slate-800 hover:border-slate-700 shadow-md' : 'border-slate-800/40 opacity-60'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                          <MessageSquare className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-white tracking-wide font-mono">{prompt.name}</h4>
                          <span className="text-[10px] text-slate-400 font-mono">{prompt.server_name}</span>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[9px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">
                        {(prompt.arguments || []).length} args
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {prompt.description || 'No description provided.'}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 font-mono">Template</span>
                    <button
                      onClick={() => handleOpenPrompt(prompt)}
                      className="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition"
                    >
                      <span>Render Template</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 5: SECURITY & AUDIT CONTROL PLANE (PHASE 6.6) */}
      {/* ========================================================================= */}
      {activeMode === 'security' && (
        <div className="space-y-6">
          {/* Header Action */}
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                Security, RBAC & Audit Control Plane
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic security policy evaluation, capability-level permissions, content trust boundaries, and real-time audit event logging.
              </p>
            </div>
            <button
              onClick={fetchSecurityData}
              disabled={isLoadingSecurity}
              className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSecurity ? 'animate-spin text-indigo-400' : ''}`} />
              <span>Refresh Security Status</span>
            </button>
          </div>

          {isLoadingSecurity ? (
            <div className="flex items-center justify-center py-16 text-slate-400 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Querying security status and audit records...</span>
            </div>
          ) : (
            <>
              {/* Security Metrics Overview Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Policy Engine</span>
                  <div className="flex items-center justify-between">
                    <strong className="text-sm text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Active (Precedence Mode)
                    </strong>
                  </div>
                  <p className="text-[11px] text-slate-500">Enforces Auth &rarr; Tenant &rarr; RBAC &rarr; Risk</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Content Trust Boundary</span>
                  <div className="flex items-center justify-between">
                    <strong className="text-sm text-purple-300 font-mono">UNTRUSTED_MCP</strong>
                  </div>
                  <p className="text-[11px] text-slate-500">External prompt & tool injection defense</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Restricted Tool Gate</span>
                  <div className="flex items-center justify-between">
                    <strong className="text-sm text-amber-400 flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5" /> Single-Use Confirmation
                    </strong>
                  </div>
                  <p className="text-[11px] text-slate-500">Cryptographically bound token replay defense</p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Network & SSRF Guard</span>
                  <div className="flex items-center justify-between">
                    <strong className="text-sm text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Hardened
                    </strong>
                  </div>
                  <p className="text-[11px] text-slate-500">Blocks 127.0.0.1, 169.254.169.254, file://</p>
                </div>
              </div>

              {/* Active RBAC Permissions */}
              {securityStatus && (
                <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-indigo-400" />
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">Active Workspace Permissions</h4>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 uppercase">
                      Role: {securityStatus.user_role}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {(securityStatus.active_permissions || []).map((perm) => (
                      <span
                        key={perm}
                        className="px-2.5 py-1 rounded-lg text-xs font-mono bg-slate-950 border border-slate-800 text-slate-300 flex items-center gap-1.5"
                      >
                        <CheckCircle className="w-3 h-3 text-emerald-400" />
                        <span>{perm}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Real-time Security Audit Log */}
              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-indigo-400" />
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Recent MCP Security Audit Events</h4>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">{auditLogs.length} events recorded</span>
                </div>

                {auditLogs.length === 0 ? (
                  <div className="p-6 rounded-xl bg-slate-950 border border-slate-800 text-center text-xs text-slate-400">
                    No MCP security audit events recorded yet for this workspace.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead>
                        <tr className="border-b border-slate-800 text-[10px] uppercase font-semibold text-slate-500">
                          <th className="p-2.5">Decision</th>
                          <th className="p-2.5">Event</th>
                          <th className="p-2.5">Reason Code</th>
                          <th className="p-2.5">Capability / Target</th>
                          <th className="p-2.5">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                        {auditLogs.map((ev) => (
                          <tr key={ev.id} className="hover:bg-slate-800/30 transition">
                            <td className="p-2.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  ev.decision === 'ALLOW'
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : ev.decision === 'REQUIRE_CONFIRMATION'
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                    : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                }`}
                              >
                                {ev.decision}
                              </span>
                            </td>
                            <td className="p-2.5 font-bold text-white">{ev.event_type}</td>
                            <td className="p-2.5 text-slate-400">{ev.reason_code}</td>
                            <td className="p-2.5 text-indigo-300 truncate max-w-[150px]">
                              {ev.capability_id ? `Cap: ${ev.capability_id.slice(0, 8)}...` : ev.server_id ? `Server: ${ev.server_id.slice(0, 8)}...` : '—'}
                            </td>
                            <td className="p-2.5 text-slate-500">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TOOL INSPECTOR & EXECUTION MODAL (PHASE 6.3 & 6.4) */}
      {/* ========================================================================= */}
      {showToolModal && selectedTool && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Wrench className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono">{selectedTool.name}</h3>
                  <p className="text-xs text-slate-400">Provided by server: <strong className="text-slate-200">{selectedTool.server_name}</strong></p>
                </div>
              </div>
              <button onClick={() => setShowToolModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Internal Tabs */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <button
                onClick={() => setToolModalTab('schema')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  toolModalTab === 'schema'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                <span>Schema & Safety</span>
              </button>
              <button
                onClick={() => setToolModalTab('execute')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  toolModalTab === 'execute'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Play className="w-3.5 h-3.5" />
                <span>Execute Tool</span>
              </button>
            </div>

            {/* TAB 1: SCHEMA & SAFETY */}
            {toolModalTab === 'schema' && (
              <div className="space-y-3.5 overflow-y-auto pr-1 text-xs">
                <div>
                  <h4 className="text-slate-300 font-semibold mb-1">Description</h4>
                  <p className="text-slate-400 leading-relaxed bg-slate-950 p-3 rounded-xl border border-slate-800">
                    {selectedTool.description || 'No description provided.'}
                  </p>
                </div>

                {/* Risk Policy Assessment */}
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-300">Deterministic Safety Policy</span>
                    <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase font-mono ${
                      selectedTool.risk_level === 'safe' 
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                        : selectedTool.risk_level === 'restricted'
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                        : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                    }`}>
                      {selectedTool.risk_level} ({selectedTool.policy_decision})
                    </span>
                  </div>
                  {selectedTool.risk_reasons && selectedTool.risk_reasons.length > 0 ? (
                    <ul className="list-disc list-inside text-amber-400 text-[11px] space-y-0.5">
                      {selectedTool.risk_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-400 text-[11px]">No high-risk execution indicators detected.</span>
                  )}
                </div>

                {/* Input Schema Parameters Table */}
                <div className="space-y-1.5">
                  <h4 className="text-slate-300 font-semibold">Parameters & Schema Properties</h4>
                  {selectedTool.input_schema?.properties && Object.keys(selectedTool.input_schema.properties).length > 0 ? (
                    <div className="border border-slate-800 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-[11px]">
                        <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800">
                          <tr>
                            <th className="p-2.5">Parameter</th>
                            <th className="p-2.5">Type</th>
                            <th className="p-2.5">Required</th>
                            <th className="p-2.5">Description</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
                          {Object.entries(selectedTool.input_schema.properties).map(([propName, propDef]) => {
                            const isReq = (selectedTool.input_schema.required || []).includes(propName);
                            return (
                              <tr key={propName}>
                                <td className="p-2.5 font-mono text-indigo-300 font-semibold">{propName}</td>
                                <td className="p-2.5 font-mono text-slate-400">{propDef.type || 'any'}</td>
                                <td className="p-2.5">
                                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono ${isReq ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-800 text-slate-400'}`}>
                                    {isReq ? 'YES' : 'OPTIONAL'}
                                  </span>
                                </td>
                                <td className="p-2.5 text-slate-300">{propDef.description || '—'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-500 text-[11px]">
                      This tool requires no input arguments (empty properties schema).
                    </div>
                  )}
                </div>

                {/* Raw JSON Schema */}
                <div className="space-y-1.5">
                  <span className="text-slate-300 font-semibold">Raw JSON Schema</span>
                  <pre className="p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-48">
                    {JSON.stringify(selectedTool.input_schema, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* TAB 2: EXECUTE TOOL (PHASE 6.4) */}
            {toolModalTab === 'execute' && (
              <div className="space-y-4 overflow-y-auto pr-1 text-xs">
                
                {/* Warning / Policy Banner */}
                {selectedTool.risk_level === 'restricted' && (
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                    <div>
                      <strong className="block font-semibold">Restricted Tool Execution Warning</strong>
                      <span>This capability performs privileged operations. A single-use confirmation token will be authorized before execution.</span>
                    </div>
                  </div>
                )}

                {/* Dynamic Parameter Inputs Form */}
                <div className="space-y-3">
                  <h4 className="text-slate-300 font-semibold">Input Arguments</h4>
                  {selectedTool.input_schema?.properties && Object.keys(selectedTool.input_schema.properties).length > 0 ? (
                    Object.entries(selectedTool.input_schema.properties).map(([propName, propDef]) => {
                      const isReq = (selectedTool.input_schema.required || []).includes(propName);
                      return (
                        <div key={propName} className="space-y-1">
                          <label className="flex items-center justify-between text-slate-300 font-medium">
                            <span className="font-mono text-indigo-300">{propName} {isReq && <span className="text-rose-400">*</span>}</span>
                            <span className="text-[10px] text-slate-500 font-mono">({propDef.type || 'string'})</span>
                          </label>
                          <input
                            type={propDef.type === 'number' || propDef.type === 'integer' ? 'number' : 'text'}
                            placeholder={propDef.description || `Enter value for ${propName}...`}
                            value={executionArgs[propName] ?? ''}
                            onChange={(e) => {
                              const val = propDef.type === 'number' || propDef.type === 'integer' 
                                ? (e.target.value === '' ? '' : Number(e.target.value))
                                : e.target.value;
                              setExecutionArgs(prev => ({ ...prev, [propName]: val }));
                            }}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                          />
                          {propDef.description && (
                            <span className="text-[10px] text-slate-500 block px-1">{propDef.description}</span>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-slate-500 italic p-3 bg-slate-950 rounded-xl border border-slate-800">
                      No parameters required for this tool.
                    </p>
                  )}
                </div>

                {/* Error Banner */}
                {executionError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{executionError}</span>
                  </div>
                )}

                {/* Execution Result Viewer */}
                {executionResult && (
                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200">Execution Output</span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-mono">
                          {executionResult.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                        <Clock className="w-3 h-3 text-indigo-400" />
                        <span>{executionResult.duration_ms}ms</span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(executionResult.result, null, 2));
                            triggerNotification?.('Copied', 'Result copied to clipboard');
                          }}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 ml-2"
                          title="Copy Output JSON"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                    <pre className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-56 leading-relaxed">
                      {JSON.stringify(executionResult.result, null, 2)}
                    </pre>
                  </div>
                )}

              </div>
            )}

            <div className="pt-2 flex justify-between items-center border-t border-slate-800">
              <button
                onClick={() => handleToggleToolEnable(selectedTool)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                  selectedTool.enabled
                    ? 'bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30'
                    : 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                }`}
              >
                <Power className="w-3.5 h-3.5" />
                <span>{selectedTool.enabled ? 'Disable Tool' : 'Enable Tool'}</span>
              </button>

              <div className="flex items-center gap-2">
                {toolModalTab === 'execute' && (
                  <button
                    onClick={handleExecute}
                    disabled={isExecuting || !selectedTool.available_for_execution}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                  >
                    {isExecuting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Executing...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        <span>Run Execution</span>
                      </>
                    )}
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
      {/* RESOURCE CONTENT INSPECTOR MODAL (PHASE 6.5) */}
      {/* ========================================================================= */}
      {showResourceModal && selectedResource && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
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
              <button onClick={() => setShowResourceModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                <div className="space-y-0.5">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Server Origin</span>
                  <p className="font-mono text-slate-300">{selectedResource.server_name}</p>
                </div>
                <div className="space-y-0.5 text-right">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">MIME Type</span>
                  <p className="font-mono text-indigo-400">{resourceContent?.mime_type || selectedResource.mime_type || 'text/plain'}</p>
                </div>
              </div>

              {isReadingResource ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-xs gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
                  <span>Connecting to MCP server and reading resource content...</span>
                </div>
              ) : resourceReadError ? (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1">
                  <span className="font-bold flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    Resource Read Failed
                  </span>
                  <p className="font-mono">{resourceReadError}</p>
                </div>
              ) : resourceContent ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">Sanitized Content Preview</span>
                    <div className="flex items-center gap-2">
                      {resourceContent.truncated && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          TRUNCATED (1MB Limit)
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-slate-400">{resourceContent.size} bytes</span>
                    </div>
                  </div>
                  <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto max-h-72 whitespace-pre-wrap leading-relaxed">
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
      {/* PROMPT TEMPLATE RENDERER MODAL (PHASE 6.5) */}
      {/* ========================================================================= */}
      {showPromptModal && selectedPrompt && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono">{selectedPrompt.name}</h3>
                  <p className="text-xs text-slate-400">Server: <strong className="text-slate-200">{selectedPrompt.server_name}</strong></p>
                </div>
              </div>
              <button onClick={() => setShowPromptModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              <p className="text-xs text-slate-400 leading-relaxed">{selectedPrompt.description || 'No description provided.'}</p>

              {/* Dynamic Arguments Form */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-300">Template Arguments</h4>
                {(selectedPrompt.arguments || []).length === 0 ? (
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-500 text-xs">
                    This template takes no required arguments.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {selectedPrompt.arguments.map((arg) => (
                      <div key={arg.name} className="space-y-1">
                        <label className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5">
                          <span>{arg.name}</span>
                          {arg.required && <span className="text-rose-400 font-bold">*</span>}
                        </label>
                        <input
                          type="text"
                          value={promptArgs[arg.name] || ''}
                          onChange={(e) => setPromptArgs({ ...promptArgs, [arg.name]: e.target.value })}
                          placeholder={arg.description || `Enter value for ${arg.name}...`}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-purple-500 transition"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {isRenderingPrompt && (
                <div className="flex items-center justify-center py-6 text-slate-400 text-xs gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
                  <span>Rendering prompt template via MCP server...</span>
                </div>
              )}

              {promptRenderError && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1">
                  <span className="font-bold flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    Render Error
                  </span>
                  <p className="font-mono">{promptRenderError}</p>
                </div>
              )}

              {renderedPrompt && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">Rendered Messages (External Untrusted Data)</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      Untrusted Data
                    </span>
                  </div>
                  <div className="space-y-2">
                    {renderedPrompt.messages.map((m, idx) => (
                      <div key={idx} className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] font-mono font-bold uppercase text-purple-400">
                          Role: {m.role}
                        </span>
                        <p className="text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {m.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-slate-800 pt-3 flex items-center justify-between">
              <button
                onClick={handleRenderPrompt}
                disabled={isRenderingPrompt}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Render Prompt</span>
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
      )}

      {/* Discovery Summary Modal */}
      {discoverySummary && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Discovery Synchronization Result
              </h3>
              <button onClick={() => setDiscoverySummary(null)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 text-xs text-slate-300">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Server:</span>
                <span className="font-semibold text-white font-mono">{discoverySummary.server_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Protocol / Server Version:</span>
                <span className="font-mono text-indigo-300">v{discoverySummary.protocol_version} (Server v{discoverySummary.server_version || '1.0.0'})</span>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Tools (+Added / ~Changed)</span>
                  <strong className="text-sm text-emerald-400">+{discoverySummary.tools_added}</strong> / <span className="text-amber-400 font-semibold">~{discoverySummary.tools_changed}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Resources (+Added / ~Changed)</span>
                  <strong className="text-sm text-emerald-400">+{discoverySummary.resources_added}</strong> / <span className="text-amber-400 font-semibold">~{discoverySummary.resources_changed}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Prompts (+Added / ~Changed)</span>
                  <strong className="text-sm text-emerald-400">+{discoverySummary.prompts_added}</strong> / <span className="text-amber-400 font-semibold">~{discoverySummary.prompts_changed}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Stale / Reactivated</span>
                  <strong className="text-sm text-rose-400">{discoverySummary.stale_capabilities}</strong> / <span className="text-indigo-400 font-semibold">{discoverySummary.reactivated_capabilities}</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 text-right">
                Latency: {discoverySummary.discovery_latency_ms}ms • Unchanged: {discoverySummary.unchanged_capabilities}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setDiscoverySummary(null)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Register Server Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Register MCP Server
              </h3>
              <button onClick={() => setShowRegisterModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Server Name *</label>
                <input
                  type="text"
                  placeholder="e.g. GitHub Workspace Server"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Connection URL / Command Path *</label>
                <input
                  type="text"
                  placeholder="e.g. http://localhost:8000/sse or mock://github"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Transport</label>
                  <select
                    value={transport}
                    onChange={(e) => setTransport(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="sse">SSE (Server-Sent Events)</option>
                    <option value="streamable_http">Streamable HTTP</option>
                    <option value="stdio">Process STDIO</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Authentication</label>
                  <select
                    value={authType}
                    onChange={(e) => setAuthType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="none">None (Open)</option>
                    <option value="api_key">API Key</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="oauth">OAuth 2.0</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Describe tools or resources this server provides..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-semibold flex items-center gap-1.5"
                >
                  {isSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isSubmitting ? 'Registering...' : 'Register Server'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Capabilities Inspection Modal */}
      {showCapabilitiesModal && selectedServer && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-wide">{selectedServer.name} Capabilities</h3>
                  <p className="text-xs text-slate-400">{capabilities.length} discovered capabilities across catalog</p>
                </div>
              </div>
              <button onClick={() => setShowCapabilitiesModal(false)} className="text-slate-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter & Search Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-b border-slate-800 pb-2 text-xs">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  onClick={() => { setActiveTab('tool'); setSelectedCap(null); }}
                  className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                    activeTab === 'tool' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Wrench className="w-3.5 h-3.5" />
                  <span>Tools ({capabilities.filter(c => c.capability_type === 'tool').length})</span>
                </button>
                <button
                  onClick={() => { setActiveTab('resource'); setSelectedCap(null); }}
                  className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                    activeTab === 'resource' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>Resources ({capabilities.filter(c => c.capability_type === 'resource').length})</span>
                </button>
                <button
                  onClick={() => { setActiveTab('prompt'); setSelectedCap(null); }}
                  className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition ${
                    activeTab === 'prompt' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Prompts ({capabilities.filter(c => c.capability_type === 'prompt').length})</span>
                </button>
              </div>

              <div className="relative w-full sm:w-56">
                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={capSearch}
                  onChange={(e) => setCapSearch(e.target.value)}
                  placeholder={`Search ${activeTab}s...`}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-1.5 pl-8 pr-3 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto min-h-[300px]">
              
              {/* Capabilities List */}
              <div className="space-y-2 overflow-y-auto pr-1">
                {isLoadingCaps ? (
                  <div className="flex items-center justify-center py-12 text-slate-400 text-xs gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                    <span>Loading capabilities...</span>
                  </div>
                ) : (
                  (activeTab === 'tool' ? toolsList : activeTab === 'resource' ? resourcesList : promptsList).length === 0 ? (
                    <div className="text-center py-12 text-slate-500 text-xs">
                      No matching {activeTab}s found. Click "Refresh" on server card to synchronize.
                    </div>
                  ) : (
                    (activeTab === 'tool' ? toolsList : activeTab === 'resource' ? resourcesList : promptsList).map((cap) => (
                      <div
                        key={cap.id}
                        onClick={() => setSelectedCap(cap)}
                        className={`p-3 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                          selectedCap?.id === cap.id 
                            ? 'bg-indigo-950/40 border-indigo-500 text-white' 
                            : cap.is_stale
                            ? 'bg-slate-950 border-amber-500/20 text-slate-400 opacity-60'
                            : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                        }`}
                      >
                        <div className="space-y-1 truncate pr-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold font-mono text-indigo-300">{cap.name}</span>
                            {cap.is_stale ? (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                STALE
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                v{cap.version || 1}
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 truncate">{cap.description || 'No description'}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
                      </div>
                    ))
                  )
                )}
              </div>

              {/* Capability Details & Schema Inspector */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-y-auto space-y-3">
                {selectedCap ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {selectedCap.capability_type}
                        </span>
                        {selectedCap.is_stale && (
                          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Stale / Disappeared
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-bold text-white font-mono mt-2">{selectedCap.name}</h4>
                      <p className="text-slate-400 text-xs mt-1 leading-relaxed">{selectedCap.description || 'No description provided.'}</p>
                    </div>

                    {selectedCap.definition_hash && (
                      <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-[10px] text-slate-400 flex items-center gap-1.5 font-mono">
                        <Tag className="w-3 h-3 text-indigo-400" />
                        <span>Hash: {selectedCap.definition_hash.slice(0, 16)}...</span>
                        <span className="ml-auto">Rev: {selectedCap.version || 1}</span>
                      </div>
                    )}

                    {selectedCap.input_schema && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-slate-300">Input Schema (JSON Schema)</span>
                        <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                          {JSON.stringify(selectedCap.input_schema, null, 2)}
                        </pre>
                      </div>
                    )}

                    {selectedCap.metadata && Object.keys(selectedCap.metadata).length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-slate-300">Metadata</span>
                        <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                          {JSON.stringify(selectedCap.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs text-center py-12">
                    <Code className="w-6 h-6 mb-2 text-slate-600" />
                    <span>Select a capability from the catalog to inspect its JSON schema, hash, and versioning details.</span>
                  </div>
                )}
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}
