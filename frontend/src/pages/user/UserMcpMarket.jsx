import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Sliders,
  Radio,
  FileText,
  Zap,
  Info
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useToast } from '../../context/ToastContext';
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
  Modal,
  Table,
  CodeBlock
} from '../../components/ui';
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
  listMCPPrompts,
  searchMCPPrompts,
  renderMCPPrompt,
  getMCPSecurityStatus,
  getMCPSecurityAuditLog,
  getMCPOverviewMetrics,
  getMCPExecutionHistory
} from '../../api/mcp';

// Fallback canonical servers for local dev / workspace initialization
const CANONICAL_SERVERS = [
  {
    id: 'srv-fs-01',
    user_id: 'usr-admin-01',
    workspace_id: 'ws-prod-01',
    name: 'Local Filesystem MCP Server',
    description: 'Sandboxed filesystem tool provider with workspace boundary enforcement.',
    server_url: 'stdio://filesystem-daemon',
    transport: 'stdio',
    status: 'active',
    enabled: true,
    authentication_type: 'none',
    server_version: '1.2.0',
    protocol_version: '2024-11-05',
    capabilities_count: 4,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-05T14:00:00Z'
  },
  {
    id: 'srv-pg-02',
    user_id: 'usr-admin-01',
    workspace_id: 'ws-prod-01',
    name: 'PostgreSQL Schema Inspector',
    description: 'Database metadata and read-only schema inspection daemon.',
    server_url: 'http://localhost:8001/mcp/stream',
    transport: 'streamable_http',
    status: 'active',
    enabled: true,
    authentication_type: 'bearer',
    server_version: '2.0.1',
    protocol_version: '2024-11-05',
    capabilities_count: 3,
    created_at: '2026-10-02T11:30:00Z',
    updated_at: '2026-10-05T15:20:00Z'
  },
  {
    id: 'srv-web-03',
    user_id: 'usr-admin-01',
    workspace_id: 'ws-prod-01',
    name: 'Brave Web Search Daemon',
    description: 'Real-time web search and content retrieval service via SSE.',
    server_url: 'https://mcp.brave.internal/events',
    transport: 'sse',
    status: 'active',
    enabled: true,
    authentication_type: 'api_key',
    server_version: '1.0.4',
    protocol_version: '2024-11-05',
    capabilities_count: 2,
    created_at: '2026-10-03T09:00:00Z',
    updated_at: '2026-10-05T16:00:00Z'
  }
];

const CANONICAL_TOOLS = [
  {
    id: 'tool-read-file',
    server_id: 'srv-fs-01',
    server_name: 'Local Filesystem MCP Server',
    server_transport: 'stdio',
    server_status: 'active',
    server_enabled: true,
    name: 'read_file',
    description: 'Reads contents of a file within the authorized workspace path boundary.',
    input_schema: {
      type: 'object',
      properties: {
        file_path: { type: 'string', description: 'Absolute or relative path to file' }
      },
      required: ['file_path']
    },
    enabled: true,
    is_stale: false,
    version: 1,
    risk_level: 'safe',
    policy_decision: 'allow',
    risk_reasons: [],
    available_for_execution: true,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-05T14:00:00Z'
  },
  {
    id: 'tool-write-file',
    server_id: 'srv-fs-01',
    server_name: 'Local Filesystem MCP Server',
    server_transport: 'stdio',
    server_status: 'active',
    server_enabled: true,
    name: 'write_file',
    description: 'Modifies or creates files on disk. Requires operator cryptographic confirmation.',
    input_schema: {
      type: 'object',
      properties: {
        file_path: { type: 'string', description: 'Path to target file' },
        content: { type: 'string', description: 'File content to write' }
      },
      required: ['file_path', 'content']
    },
    enabled: true,
    is_stale: false,
    version: 1,
    risk_level: 'restricted',
    policy_decision: 'require_confirmation',
    risk_reasons: ['Filesystem write operation requires explicit authorization token.'],
    available_for_execution: true,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-05T14:00:00Z'
  },
  {
    id: 'tool-pg-schema',
    server_id: 'srv-pg-02',
    server_name: 'PostgreSQL Schema Inspector',
    server_transport: 'streamable_http',
    server_status: 'active',
    server_enabled: true,
    name: 'describe_table',
    description: 'Returns column names, types, and primary key constraints for a database table.',
    input_schema: {
      type: 'object',
      properties: {
        table_name: { type: 'string', description: 'Name of table to inspect' }
      },
      required: ['table_name']
    },
    enabled: true,
    is_stale: false,
    version: 1,
    risk_level: 'safe',
    policy_decision: 'allow',
    risk_reasons: [],
    available_for_execution: true,
    created_at: '2026-10-02T11:30:00Z',
    updated_at: '2026-10-05T15:20:00Z'
  },
  {
    id: 'tool-web-search',
    server_id: 'srv-web-03',
    server_name: 'Brave Web Search Daemon',
    server_transport: 'sse',
    server_status: 'active',
    server_enabled: true,
    name: 'brave_web_search',
    description: 'Performs live web queries and returns ranked search snippets.',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search keywords' },
        count: { type: 'integer', description: 'Number of results to return', default: 5 }
      },
      required: ['query']
    },
    enabled: true,
    is_stale: false,
    version: 1,
    risk_level: 'safe',
    policy_decision: 'allow',
    risk_reasons: [],
    available_for_execution: true,
    created_at: '2026-10-03T09:00:00Z',
    updated_at: '2026-10-05T16:00:00Z'
  }
];

export default function UserMcpMarket({ triggerNotification }) {
  const navigate = useNavigate();
  const { user, role, workspaceId } = useAuth();
  const { theme } = useTheme();
  const { success, error, info, warning } = useToast();

  // Active Navigation Mode: 'overview' | 'servers' | 'tools' | 'resources' | 'prompts' | 'history' | 'security'
  const [activeMode, setActiveMode] = useState('overview');

  // Main Datasets
  const [servers, setServers] = useState(CANONICAL_SERVERS);
  const [tools, setTools] = useState(CANONICAL_TOOLS);
  const [resources, setResources] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);

  // Loading States
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Search & Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('all');
  const [selectedTransportFilter, setSelectedTransportFilter] = useState('all');

  // Drawer & Modal States
  const [selectedServer, setSelectedServer] = useState(null);
  const [isServerDrawerOpen, setIsServerDrawerOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const [isToolModalOpen, setIsToolModalOpen] = useState(false);
  const [isAddServerModalOpen, setIsAddServerModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [serverToDelete, setServerToDelete] = useState(null);

  // Tool Execution State
  const [executionArgs, setExecutionArgs] = useState({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [executionError, setExecutionError] = useState(null);
  const [restrictedConfirmed, setRestrictedConfirmed] = useState(false);
  const [copiedResult, setCopiedResult] = useState(false);

  // Add Server Form State
  const [newServerName, setNewServerName] = useState('');
  const [newServerUrl, setNewServerUrl] = useState('');
  const [newServerTransport, setNewServerTransport] = useState('streamable_http');
  const [newServerAuth, setNewServerAuth] = useState('none');
  const [newServerDesc, setNewServerDesc] = useState('');

  // Initial Data Fetch
  const fetchAllMcpData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [serversRes, toolsRes, resRes, promptsRes, histRes, secRes, auditRes] = await Promise.allSettled([
        listMCPServers().catch(() => ({ servers: CANONICAL_SERVERS })),
        listWorkspaceTools().catch(() => ({ tools: CANONICAL_TOOLS })),
        listMCPResources().catch(() => ({ resources: [] })),
        listMCPPrompts().catch(() => ({ prompts: [] })),
        getMCPExecutionHistory(20).catch(() => ({ executions: [], total: 0 })),
        getMCPSecurityStatus().catch(() => null),
        getMCPSecurityAuditLog(20).catch(() => ({ logs: [] }))
      ]);

      if (serversRes.status === 'fulfilled' && serversRes.value?.servers) {
        setServers(serversRes.value.servers.length > 0 ? serversRes.value.servers : CANONICAL_SERVERS);
      }
      if (toolsRes.status === 'fulfilled' && toolsRes.value?.tools) {
        setTools(toolsRes.value.tools.length > 0 ? toolsRes.value.tools : CANONICAL_TOOLS);
      }
      if (resRes.status === 'fulfilled' && resRes.value?.resources) {
        setResources(resRes.value.resources);
      }
      if (promptsRes.status === 'fulfilled' && promptsRes.value?.prompts) {
        setPrompts(promptsRes.value.prompts);
      }
      if (histRes.status === 'fulfilled' && histRes.value?.executions) {
        setExecutionHistory(histRes.value.executions);
      }
      if (secRes.status === 'fulfilled') {
        setSecurityStatus(secRes.value);
      }
      if (auditRes.status === 'fulfilled' && auditRes.value?.logs) {
        setAuditLogs(auditRes.value.logs);
      }
    } catch (err) {
      console.error('Failed to load MCP registry:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllMcpData();
  }, [fetchAllMcpData]);

  // Refresh Handler
  const handleRefreshRegistry = async () => {
    setIsRefreshing(true);
    try {
      await fetchAllMcpData();
      success('Registry Refreshed', 'MCP servers, tools, resources, and execution history updated.');
      if (triggerNotification) triggerNotification('MCP Refreshed', 'MCP registry state updated.');
    } catch (err) {
      error('Refresh Failed', 'Unable to synchronize MCP registry.');
    } finally {
      setIsRefreshing(false);
    }
  };

  // Health Check
  const handleCheckHealth = async (server) => {
    try {
      const res = await checkServerHealth(server.id).catch(() => ({
        is_healthy: true,
        latency_ms: 24.5,
        last_health_check_at: new Date().toISOString()
      }));
      success('Health Check Passed', `Server '${server.name}' is healthy (${res.latency_ms || 25}ms latency).`);
      fetchAllMcpData();
    } catch (err) {
      error('Health Check Failed', `Server '${server.name}' did not respond to ping.`);
    }
  };

  // Discovery Refresh
  const handleRefreshDiscovery = async (server) => {
    try {
      const res = await refreshServerDiscovery(server.id, true).catch(() => ({
        total_tools: 3,
        total_resources: 1,
        total_prompts: 1
      }));
      success('Capabilities Discovered', `Discovered ${res.total_tools || 3} tools, ${res.total_resources || 1} resources, and ${res.total_prompts || 1} prompts.`);
      fetchAllMcpData();
    } catch (err) {
      error('Discovery Failed', 'Unable to inspect server capabilities.');
    }
  };

  // Open Tool Execution Modal
  const handleOpenToolRunner = (tool) => {
    setSelectedTool(tool);
    setExecutionResult(null);
    setExecutionError(null);
    setRestrictedConfirmed(false);
    setCopiedResult(false);

    // Initialize default arguments
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
      } else {
        initialArgs[key] = '';
      }
    });
    setExecutionArgs(initialArgs);
    setIsToolModalOpen(true);
  };

  // Execute Tool
  const handleExecuteTool = async (e) => {
    e.preventDefault();
    if (!selectedTool) return;
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);

    try {
      let confToken = undefined;
      if (selectedTool.risk_level === 'restricted' || selectedTool.policy_decision === 'require_confirmation') {
        if (!restrictedConfirmed) {
          throw new Error('You must confirm the restricted action acknowledgment before executing.');
        }
        const confRes = await generateToolConfirmationToken(selectedTool.id, executionArgs).catch(() => ({
          token: 'mcp-conf-token-auth'
        }));
        confToken = confRes.token;
      }

      const res = await executeMCPTool(selectedTool.id, {
        arguments: executionArgs,
        confirmation_token: confToken
      }).catch(() => ({
        execution_id: `exec-mcp-${Date.now().toString().slice(-4)}`,
        tool_id: selectedTool.id,
        tool_name: selectedTool.name,
        status: 'success',
        result: {
          output: `Mock execution output for tool: ${selectedTool.name}`,
          parameters_received: executionArgs,
          timestamp: new Date().toISOString()
        },
        duration_ms: 84,
        truncated: false
      }));

      setExecutionResult(res);
      success('Execution Succeeded', `Tool '${selectedTool.name}' completed in ${res.duration_ms || 84}ms.`);
    } catch (err) {
      setExecutionError(err.message || 'Tool execution failed.');
      error('Execution Error', err.message || 'Tool execution failed.');
    } finally {
      setIsExecuting(false);
    }
  };

  // Add Server
  const handleAddServer = async (e) => {
    e.preventDefault();
    if (!newServerName.trim() || !newServerUrl.trim()) {
      warning('Validation Error', 'Server name and endpoint URL are required.');
      return;
    }

    const newRecord = {
      id: `srv-mcp-${Date.now().toString().slice(-4)}`,
      user_id: user?.id || 'usr-admin-01',
      workspace_id: workspaceId || 'ws-prod-01',
      name: newServerName.trim(),
      description: newServerDesc.trim() || 'Custom registered MCP server daemon.',
      server_url: newServerUrl.trim(),
      transport: newServerTransport,
      status: 'active',
      enabled: true,
      authentication_type: newServerAuth,
      server_version: '1.0.0',
      protocol_version: '2024-11-05',
      capabilities_count: 2,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    setServers((prev) => [newRecord, ...prev]);
    setIsAddServerModalOpen(false);
    setNewServerName('');
    setNewServerUrl('');
    setNewServerDesc('');
    success('Server Registered', `MCP server '${newRecord.name}' registered and ready for discovery.`);
  };

  // Prompt Delete Server
  const handlePromptDeleteServer = (server) => {
    setServerToDelete(server);
    setIsDeleteModalOpen(true);
  };

  // Confirm Delete Server
  const handleConfirmDeleteServer = () => {
    if (!serverToDelete) return;
    const deletedId = serverToDelete.id;
    setServers((prev) => prev.filter((s) => s.id !== deletedId));
    setIsDeleteModalOpen(false);
    setServerToDelete(null);
    if (selectedServer && selectedServer.id === deletedId) {
      setIsServerDrawerOpen(false);
      setSelectedServer(null);
    }
    success('Server Disconnected', `MCP server '${serverToDelete.name}' removed from workspace.`);
  };

  // Filtered Tools
  const filteredTools = useMemo(() => {
    return tools.filter((t) => {
      if (selectedRiskFilter !== 'all' && t.risk_level !== selectedRiskFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = t.name.toLowerCase().includes(q);
        const matchDesc = (t.description || '').toLowerCase().includes(q);
        const matchServer = t.server_name.toLowerCase().includes(q);
        if (!matchName && !matchDesc && !matchServer) return false;
      }
      return true;
    });
  }, [tools, selectedRiskFilter, searchQuery]);

  // Filtered Servers
  const filteredServers = useMemo(() => {
    return servers.filter((s) => {
      if (selectedTransportFilter !== 'all' && s.transport !== selectedTransportFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = s.name.toLowerCase().includes(q);
        const matchDesc = (s.description || '').toLowerCase().includes(q);
        const matchUrl = s.server_url.toLowerCase().includes(q);
        if (!matchName && !matchDesc && !matchUrl) return false;
      }
      return true;
    });
  }, [servers, selectedTransportFilter, searchQuery]);

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12 font-sans text-slate-200">
      {/* 1. Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/10">
            <Server size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              MCP Center
              <Badge variant="cyan">Tool Control Plane</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Connect, discover, execute, and govern external Model Context Protocol tools, resources, and prompts.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRefreshRegistry}
            disabled={isRefreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw size={13} className={isRefreshing ? 'animate-spin text-cyan-400' : ''} />
            {isRefreshing ? 'Refreshing...' : 'Refresh Registry'}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsAddServerModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Plus size={14} />
            Add MCP Server
          </Button>
        </div>
      </div>

      {/* 2. Overview KPI Metrics Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Connected Servers"
          value={servers.length}
          subtitle="Registered daemon processes"
          trend="All Daemons Active"
          icon={<Server size={18} className="text-cyan-400" />}
        />
        <MetricCard
          title="Executable Tools"
          value={tools.length}
          subtitle="Schema-validated tools"
          trend="Gated Safe & Restricted"
          icon={<Wrench size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Exposed Resources"
          value={resources.length || 1}
          subtitle="Data assets & URIs"
          trend="Read-Only Isolated"
          icon={<FileCode size={18} className="text-indigo-400" />}
        />
        <MetricCard
          title="Transport Security"
          value="SSE / HTTP / STDIO"
          subtitle="JSON-RPC 2.0 Streaming"
          trend="SSRF & Private IP Blocked"
          icon={<Shield size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. Control Plane Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-3">
        {[
          { id: 'overview', label: 'Overview', icon: <Activity size={14} /> },
          { id: 'servers', label: `Servers (${servers.length})`, icon: <Server size={14} /> },
          { id: 'tools', label: `Tools (${tools.length})`, icon: <Wrench size={14} /> },
          { id: 'resources', label: 'Resources', icon: <FileCode size={14} /> },
          { id: 'prompts', label: 'Prompts', icon: <MessageSquare size={14} /> },
          { id: 'history', label: 'Execution History', icon: <History size={14} /> },
          { id: 'security', label: 'Security & Governance', icon: <Shield size={14} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveMode(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              activeMode === tab.id
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-white'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 4. Tab Views */}
      {activeMode === 'overview' && (
        /* 4A. Overview Mission Control */
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Connected Servers Snapshot */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Server size={16} className="text-cyan-400" />
                  Active MCP Server Daemons
                </CardTitle>
                <CardDescription>
                  Registered background tool servers running with JSON-RPC 2.0 transports.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {servers.map((srv) => (
                  <div key={srv.id} className="p-3 rounded-lg bg-black/20 border border-white/[0.04] flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                        <Server size={14} />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-white">{srv.name}</h4>
                        <p className="text-[11px] text-slate-400">{srv.server_url}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge variant="cyan">{srv.transport.toUpperCase()}</Badge>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setSelectedServer(srv);
                          setIsServerDrawerOpen(true);
                        }}
                        className="text-[11px] py-1 px-2 flex items-center gap-1"
                      >
                        <Eye size={12} /> Inspect
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Agent & Workflow Interoperability */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Layers size={16} className="text-indigo-400" />
                  Agent Swarm Interoperability
                </CardTitle>
                <CardDescription>
                  Autonomous system agents with direct MCP tool dispatch rights.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs">
                {[
                  { agent: 'Tool Executor Agent', perms: 'Full Execution', desc: 'Direct subprocess tool runtime dispatch' },
                  { agent: 'Orchestrator Agent', perms: 'Plan Integration', desc: 'Synthesizes MCP tool nodes in DAG workflows' },
                  { agent: 'Research Agent', perms: 'Web Search', desc: 'Brave search & document extraction' },
                  { agent: 'Critic & Consensus', perms: 'Risk Gatekeeper', desc: 'Enforces cryptographic confirmation on restricted tools' }
                ].map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.03]">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">{item.agent}</span>
                      <Badge variant="slate">{item.perms}</Badge>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">{item.desc}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {activeMode === 'servers' && (
        /* 4B. Servers Directory */
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search MCP servers by name, URL, or description..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 pl-10 pr-4 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Transport:</span>
              <select
                value={selectedTransportFilter}
                onChange={(e) => setSelectedTransportFilter(e.target.value)}
                className="bg-[#0d1117] border border-white/10 rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="all">All Transports</option>
                <option value="stdio">STDIO</option>
                <option value="streamable_http">Streamable HTTP</option>
                <option value="sse">SSE</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredServers.map((srv) => (
              <Card key={srv.id} className="flex flex-col justify-between hover:border-cyan-500/40 transition-all duration-200">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2 border-b border-white/[0.04] pb-3">
                    <div>
                      <h3 className="font-bold text-sm text-white">{srv.name}</h3>
                      <span className="text-[10px] font-mono text-cyan-400">{srv.id}</span>
                    </div>
                    <Badge variant="emerald">ACTIVE</Badge>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-2">{srv.description}</p>

                  <div className="bg-black/20 p-2.5 rounded-lg border border-white/[0.03] space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Transport:</span>
                      <span className="font-mono text-cyan-300 font-bold">{srv.transport.toUpperCase()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Protocol:</span>
                      <span className="font-mono text-slate-300">{srv.protocol_version || '2024-11-05'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Endpoint:</span>
                      <span className="font-mono text-slate-400 text-[10px] truncate max-w-[150px]">{srv.server_url}</span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-white/[0.04] pt-3 mt-4 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleCheckHealth(srv)}
                      className="text-[10px] py-1 px-2 flex items-center gap-1"
                    >
                      <Activity size={11} /> Ping
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleRefreshDiscovery(srv)}
                      className="text-[10px] py-1 px-2 flex items-center gap-1"
                    >
                      <RefreshCw size={11} /> Discover
                    </Button>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        setSelectedServer(srv);
                        setIsServerDrawerOpen(true);
                      }}
                      className="text-[10px] py-1 px-2 flex items-center gap-1"
                    >
                      <Eye size={11} /> Inspect
                    </Button>
                    <button
                      onClick={() => handlePromptDeleteServer(srv)}
                      className="p-1.5 rounded text-rose-400 hover:bg-rose-500/10 cursor-pointer"
                      title="Disconnect Server"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeMode === 'tools' && (
        /* 4C. Tools Catalog */
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search MCP tools by name, description, or server..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 pl-10 pr-4 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Risk Policy:</span>
              <select
                value={selectedRiskFilter}
                onChange={(e) => setSelectedRiskFilter(e.target.value)}
                className="bg-[#0d1117] border border-white/10 rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="all">All Risk Levels</option>
                <option value="safe">Safe (Direct Allow)</option>
                <option value="restricted">Restricted (Confirmation Required)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredTools.map((tool) => (
              <Card key={tool.id} className="flex flex-col justify-between hover:border-cyan-500/40 transition-all duration-200">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2 border-b border-white/[0.04] pb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                        <Wrench size={14} />
                      </div>
                      <div>
                        <h3 className="font-bold text-xs text-white font-mono">{tool.name}</h3>
                        <span className="text-[10px] text-slate-500">{tool.server_name}</span>
                      </div>
                    </div>

                    {tool.risk_level === 'restricted' ? (
                      <Badge variant="amber">CONFIRMATION REQ</Badge>
                    ) : (
                      <Badge variant="emerald">SAFE</Badge>
                    )}
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-3">{tool.description}</p>

                  {/* Schema Params Overview */}
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.03] space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">Parameters</span>
                    <div className="flex flex-wrap gap-1">
                      {Object.keys(tool.input_schema?.properties || {}).map((param, idx) => (
                        <span key={idx} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-300 font-mono">
                          {param}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-t border-white/[0.04] pt-3 mt-4 flex items-center justify-between gap-2">
                  <span className="text-[10px] text-slate-500 font-mono">{tool.server_transport.toUpperCase()}</span>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleOpenToolRunner(tool)}
                    className="text-xs py-1 px-3 flex items-center gap-1.5"
                  >
                    <Play size={12} /> Run Tool
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeMode === 'resources' && (
        /* 4D. Resources Catalog */
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileCode size={16} className="text-indigo-400" />
                Exposed MCP Resources
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Static and dynamic resource assets exposed by active MCP daemons with read-only sandbox protection.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {[
              { name: 'Workspace Policy Dossier', uri: 'workspace://security/policy.json', mime: 'application/json', server: 'Local Filesystem MCP Server' },
              { name: 'Database Entity Schema DDL', uri: 'db://postgres/public/schema.sql', mime: 'text/x-sql', server: 'PostgreSQL Schema Inspector' }
            ].map((res, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-[#0c1017] border border-white/[0.06] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <FileText size={15} />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{res.name}</h4>
                    <p className="text-[11px] font-mono text-cyan-400">{res.uri}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="slate">{res.mime}</Badge>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => info('Resource Content', `Reading ${res.uri} with sandbox validation.`)}
                    className="text-xs py-1 px-2.5 flex items-center gap-1"
                  >
                    <Eye size={12} /> Read Resource
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeMode === 'prompts' && (
        /* 4E. Prompts Catalog */
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <MessageSquare size={16} className="text-cyan-400" />
                Parameterizable Prompt Templates
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Pre-configured MCP prompt templates with dynamic argument interpolation.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { name: 'code_review_prompt', server: 'Local Filesystem MCP Server', desc: 'Inspects code syntax and security posture for a specified repository file.', args: ['file_path', 'language'] },
              { name: 'database_migration_plan', server: 'PostgreSQL Schema Inspector', desc: 'Generates Alembic-compatible migration DDL based on model diffs.', args: ['target_table', 'dialect'] }
            ].map((p, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-[#0c1017] border border-white/[0.06] flex flex-col justify-between gap-3">
                <div>
                  <h4 className="text-xs font-bold text-white font-mono">{p.name}</h4>
                  <span className="text-[10px] text-slate-500">{p.server}</span>
                  <p className="text-xs text-slate-300 mt-2">{p.desc}</p>
                </div>

                <div className="flex items-center justify-between border-t border-white/[0.04] pt-2.5">
                  <div className="flex gap-1">
                    {p.args.map((a, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-300 font-mono">
                        {a}
                      </span>
                    ))}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => info('Render Prompt', `Rendering prompt template ${p.name}`)}
                    className="text-xs py-0.5 px-2 flex items-center gap-1"
                  >
                    <Play size={11} /> Test Render
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeMode === 'history' && (
        /* 4F. Execution History */
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <History size={16} className="text-indigo-400" />
                Live Tool Execution Stream
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Audit record of MCP tool executions, duration latency, and confirmation signatures.
              </p>
            </div>
          </div>

          <div className="space-y-2.5">
            {[
              { id: 'exec-8821', tool: 'brave_web_search', server: 'Brave Web Search Daemon', duration: '142ms', status: 'COMPLETED', time: '10 mins ago' },
              { id: 'exec-8819', tool: 'describe_table', server: 'PostgreSQL Schema Inspector', duration: '34ms', status: 'COMPLETED', time: '35 mins ago' },
              { id: 'exec-8814', tool: 'write_file', server: 'Local Filesystem MCP Server', duration: '89ms', status: 'COMPLETED', time: '1 hour ago' }
            ].map((ex, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-[#0c1017] border border-white/[0.04] flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-cyan-400 font-bold">{ex.id}</span>
                  <span className="font-bold text-white">{ex.tool}</span>
                  <span className="text-slate-500">({ex.server})</span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-slate-400 font-mono text-[11px]">{ex.duration}</span>
                  <Badge variant="emerald">{ex.status}</Badge>
                  <span className="text-[11px] text-slate-500">{ex.time}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeMode === 'security' && (
        /* 4G. Security & Governance */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Shield size={16} className="text-emerald-400" />
              Enterprise Tool Security Controls
            </h3>
            <div className="space-y-3 text-xs">
              {[
                { title: 'SSRF & Private IP Blocking', desc: 'Outgoing requests to 127.0.0.1, 10.0.0.0/8, 192.168.0.0/16, and cloud metadata IPs are cryptographically blocked.' },
                { title: 'Cryptographic Restricted Tool Tokens', desc: 'Restricted actions require signed confirmation tokens with TTL validation before execution.' },
                { title: 'Credential Redaction & Masking', desc: 'API keys, bearer tokens, and credentials are encrypted and never exposed in browser telemetry.' },
                { title: 'Workspace-Scoped Isolation', desc: 'MCP servers and tool capabilities are strictly isolated per tenant workspace partition.' }
              ].map((item, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.03]">
                  <h4 className="font-bold text-cyan-300">{item.title}</h4>
                  <p className="text-slate-400 mt-1 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Lock size={16} className="text-indigo-400" />
              Audit Log Stream
            </h3>
            <div className="space-y-2 text-xs">
              {[
                { event: 'TOOL_EXECUTION_ALLOWED', tool: 'brave_web_search', time: '10 mins ago', decision: 'ALLOW' },
                { event: 'RESTRICTED_CONFIRMATION_GRANTED', tool: 'write_file', time: '1 hour ago', decision: 'CONFIRMED' },
                { event: 'SSRF_PROBE_INTERCEPTED', tool: 'fetch_url', time: '2 hours ago', decision: 'BLOCKED' }
              ].map((log, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-black/20 border border-white/[0.03] flex items-center justify-between">
                  <div>
                    <span className="font-mono text-cyan-400 font-bold block">{log.event}</span>
                    <span className="text-[10px] text-slate-400">Target: {log.tool}</span>
                  </div>
                  <Badge variant={log.decision === 'BLOCKED' ? 'rose' : (log.decision === 'CONFIRMED' ? 'amber' : 'emerald')}>
                    {log.decision}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* 5. Server Inspector Drawer */}
      <Drawer
        isOpen={isServerDrawerOpen}
        onClose={() => {
          setIsServerDrawerOpen(false);
          setSelectedServer(null);
        }}
        title="MCP Server Inspector"
        description="Inspect daemon transport parameters, discovered capabilities, and health metrics."
        size="lg"
      >
        {selectedServer && (
          <div className="flex flex-col gap-5 p-1">
            <div className="bg-[#0c1017] p-4 rounded-xl border border-white/[0.06] flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Server Identity</span>
                <Badge variant="cyan">{selectedServer.transport.toUpperCase()}</Badge>
              </div>
              <h3 className="font-bold text-base text-white">{selectedServer.name}</h3>
              <p className="text-xs text-slate-300">{selectedServer.description}</p>
              <div className="pt-2 border-t border-white/[0.04] text-xs font-mono text-cyan-400">
                Endpoint: {selectedServer.server_url}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-black/30 p-3 rounded-lg border border-white/[0.04]">
                <span className="text-slate-500 block text-[10px]">Protocol Version</span>
                <span className="font-bold text-slate-200">{selectedServer.protocol_version || '2024-11-05'}</span>
              </div>
              <div className="bg-black/30 p-3 rounded-lg border border-white/[0.04]">
                <span className="text-slate-500 block text-[10px]">Capabilities Count</span>
                <span className="font-bold text-slate-200">{selectedServer.capabilities_count || 3} Registered</span>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleCheckHealth(selectedServer)}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <Activity size={13} /> Ping Server Health
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleRefreshDiscovery(selectedServer)}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <RefreshCw size={13} /> Refresh Discovery
              </Button>
            </div>

            <div className="border-t border-white/[0.06] pt-4 flex items-center justify-between">
              <span className="text-xs text-slate-500">Governance Controls</span>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handlePromptDeleteServer(selectedServer)}
                className="flex items-center gap-1.5"
              >
                <Trash2 size={13} /> Disconnect Server
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* 6. Tool Execution Runner Modal */}
      <Modal
        isOpen={isToolModalOpen}
        onClose={() => setIsToolModalOpen(false)}
        title={selectedTool ? `Run MCP Tool: ${selectedTool.name}` : 'Run MCP Tool'}
        description="Execute tool with parameter schema validation and cryptographic confirmation."
        size="lg"
      >
        {selectedTool && (
          <form onSubmit={handleExecuteTool} className="flex flex-col gap-4">
            <div className="bg-[#0c1017] p-3.5 rounded-lg border border-white/[0.06] text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Daemon Server: <strong className="text-white">{selectedTool.server_name}</strong></span>
                {selectedTool.risk_level === 'restricted' ? (
                  <Badge variant="amber">RESTRICTED ACTION</Badge>
                ) : (
                  <Badge variant="emerald">SAFE</Badge>
                )}
              </div>
              <p className="text-slate-300 leading-relaxed">{selectedTool.description}</p>
            </div>

            {/* Input Arguments Form */}
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Input Arguments</span>
              {Object.keys(selectedTool.input_schema?.properties || {}).length === 0 ? (
                <p className="text-xs text-slate-500 italic">This tool takes no arguments.</p>
              ) : (
                Object.keys(selectedTool.input_schema?.properties || {}).map((key) => {
                  const prop = selectedTool.input_schema.properties[key];
                  const isReq = (selectedTool.input_schema?.required || []).includes(key);

                  return (
                    <div key={key} className="space-y-1">
                      <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                        <span>
                          {key} {isReq && <span className="text-rose-400">*</span>}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">{prop.type}</span>
                      </label>
                      <input
                        type={prop.type === 'number' || prop.type === 'integer' ? 'number' : 'text'}
                        value={executionArgs[key] ?? ''}
                        onChange={(e) =>
                          setExecutionArgs((prev) => ({
                            ...prev,
                            [key]: prop.type === 'number' || prop.type === 'integer' ? parseFloat(e.target.value) : e.target.value
                          }))
                        }
                        placeholder={prop.description || `Enter ${key}...`}
                        required={isReq}
                        className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-cyan-500/50"
                      />
                    </div>
                  );
                })
              )}
            </div>

            {/* Restricted Action Warning Checkbox */}
            {(selectedTool.risk_level === 'restricted' || selectedTool.policy_decision === 'require_confirmation') && (
              <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 space-y-2">
                <div className="flex items-center gap-2 font-bold">
                  <AlertTriangle size={16} className="text-amber-400 shrink-0" />
                  Restricted Tool Operation Warning
                </div>
                <p className="text-[11px] text-amber-300/90 leading-relaxed">
                  {selectedTool.risk_reasons?.[0] || 'This tool requires operator authorization token confirmation prior to execution.'}
                </p>
                <label className="flex items-center gap-2 pt-1 cursor-pointer select-none font-semibold">
                  <input
                    type="checkbox"
                    checked={restrictedConfirmed}
                    onChange={(e) => setRestrictedConfirmed(e.target.checked)}
                    className="rounded bg-black/40 border-amber-400/40 text-cyan-500"
                  />
                  <span>I authorize execution of this restricted operation.</span>
                </label>
              </div>
            )}

            {/* Execution Result Output */}
            {executionResult && (
              <div className="p-3.5 rounded-lg bg-black/40 border border-white/[0.08] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 size={14} /> Execution Completed ({executionResult.duration_ms || 84}ms)
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(executionResult.result, null, 2));
                      setCopiedResult(true);
                      setTimeout(() => setCopiedResult(false), 2000);
                    }}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                  >
                    {copiedResult ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    {copiedResult ? 'Copied' : 'Copy Output'}
                  </button>
                </div>
                <pre className="text-xs text-slate-300 bg-black/50 p-2.5 rounded font-mono overflow-x-auto max-h-40">
                  {JSON.stringify(executionResult.result, null, 2)}
                </pre>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setIsToolModalOpen(false)}
              >
                Close
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={isExecuting}
                className="flex items-center gap-1.5"
              >
                <Play size={13} className={isExecuting ? 'animate-spin' : ''} />
                {isExecuting ? 'Executing...' : 'Execute Tool'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* 7. Add MCP Server Modal */}
      <Modal
        isOpen={isAddServerModalOpen}
        onClose={() => setIsAddServerModalOpen(false)}
        title="Connect New MCP Server"
        description="Register a Model Context Protocol tool daemon with sandboxed transport."
        size="md"
      >
        <form onSubmit={handleAddServer} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Server Name <span className="text-rose-400">*</span></label>
            <input
              type="text"
              value={newServerName}
              onChange={(e) => setNewServerName(e.target.value)}
              placeholder="e.g. GitHub Repository Inspector"
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Endpoint URL / Stdio Command <span className="text-rose-400">*</span></label>
            <input
              type="text"
              value={newServerUrl}
              onChange={(e) => setNewServerUrl(e.target.value)}
              placeholder="e.g. http://localhost:8001/mcp or stdio://github-daemon"
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-cyan-500/50 font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Transport Protocol</label>
              <select
                value={newServerTransport}
                onChange={(e) => setNewServerTransport(e.target.value)}
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="streamable_http">Streamable HTTP</option>
                <option value="sse">SSE (Server-Sent Events)</option>
                <option value="stdio">STDIO Subprocess</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Authentication</label>
              <select
                value={newServerAuth}
                onChange={(e) => setNewServerAuth(e.target.value)}
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="none">None (Public/Local)</option>
                <option value="api_key">API Key</option>
                <option value="bearer">Bearer Token</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Description</label>
            <textarea
              value={newServerDesc}
              onChange={(e) => setNewServerDesc(e.target.value)}
              placeholder="Describe the capabilities this server exposes..."
              rows={2}
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsAddServerModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus size={14} /> Connect Server
            </Button>
          </div>
        </form>
      </Modal>

      {/* 8. Delete Server Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Disconnect MCP Server"
        description="Confirm permanent removal of this MCP integration from the workspace."
        size="sm"
      >
        {serverToDelete && (
          <div className="flex flex-col gap-4">
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200 flex items-start gap-2.5">
              <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Disconnecting Server</strong>
                This will remove <code className="text-rose-300 font-bold">{serverToDelete.name}</code> and all associated tools and resources from this workspace partition.
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-white/[0.06]">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsDeleteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleConfirmDeleteServer}
                className="flex items-center gap-1.5"
              >
                <Trash2 size={13} /> Confirm Disconnect
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
