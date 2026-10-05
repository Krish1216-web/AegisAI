import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Workflow as WorkflowIcon,
  Play,
  CheckCircle2,
  AlertCircle,
  Pause,
  Archive,
  Trash2,
  Plus,
  RefreshCw,
  Eye,
  Check,
  X,
  Code,
  Shield,
  Layers,
  Activity,
  ChevronRight,
  Clock,
  Terminal,
  FileCode,
  Edit3,
  Copy,
  Search,
  SlidersHorizontal,
  Calendar,
  ShieldCheck,
  BarChart3,
  ArrowRight,
  FileText
} from 'lucide-react';
import {
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  validateWorkflow,
  activateWorkflow,
  pauseWorkflow,
  archiveWorkflow,
  executeWorkflow,
  getWorkflowExecutions,
  cloneWorkflow
} from '../../api/workflows';
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
import UserWorkflowApprovals from './UserWorkflowApprovals';
import UserWorkflowSchedules from './UserWorkflowSchedules';
import UserWorkflowAnalytics from './UserWorkflowAnalytics';

export default function UserWorkflows({ addLog, triggerNotification }) {
  const navigate = useNavigate();
  const { workspaceId, role } = useAuth();
  const { success, error, warning, info } = useToast();

  const [activeTab, setActiveTab] = useState('workflows'); // 'workflows' | 'approvals' | 'schedules' | 'analytics'
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('updated'); // 'updated' | 'name' | 'nodes'

  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [executions, setExecutions] = useState([]);

  // Modals & Drawers
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [showDetailDrawer, setShowDetailDrawer] = useState(false);
  const [showOutlineModal, setShowOutlineModal] = useState(false);
  const [workflowToDelete, setWorkflowToDelete] = useState(null);

  // Form states
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');
  const [templateChoice, setTemplateChoice] = useState('agent_pipeline'); // 'agent_pipeline' | 'rag_research' | 'blank'
  const [executeInput, setExecuteInput] = useState('{\n  "message": "Hello AegisAI Workflow",\n  "count": 5\n}');
  const [executionResult, setExecutionResult] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const fetchWorkflows = async () => {
    try {
      setLoading(true);
      const res = await getWorkflows();
      setWorkflows(res.workflows || []);
    } catch (err) {
      console.error('Failed to load workflows:', err);
      error('Workflows Error', 'Failed to fetch workflows from backend.');
      if (addLog) addLog('Workflows', 'Failed to fetch workflows from backend.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const handleCreateWorkflow = async (e) => {
    e?.preventDefault();
    if (!newWorkflowName.trim()) {
      warning('Validation Error', 'Workflow name is required.');
      return;
    }

    let nodes = [];
    let edges = [];
    let variables = [
      { name: 'env_name', value: 'Production', value_type: 'string', is_secret: false }
    ];

    if (templateChoice === 'agent_pipeline') {
      nodes = [
        {
          node_key: 'start_1',
          node_type: 'start',
          name: 'Start Trigger',
          config: { input_schema: { type: 'object' } },
          position: { x: 50, y: 150 }
        },
        {
          node_key: 'agent_research',
          node_type: 'agent',
          name: 'Research Agent',
          config: { agent_name: 'Research Agent', instruction: 'Perform deep analysis on input parameters.' },
          position: { x: 280, y: 150 }
        },
        {
          node_key: 'transform_1',
          node_type: 'transform',
          name: 'Data Formatter',
          config: {
            mapping: {
              report: '{{nodes.agent_research.output.result}}',
              environment: '{{variables.env_name}}'
            }
          },
          position: { x: 520, y: 150 }
        },
        {
          node_key: 'end_1',
          node_type: 'end',
          name: 'Final Output',
          config: {
            output_template: 'Pipeline Completed: {{nodes.transform_1.output.transformed.report}}'
          },
          position: { x: 760, y: 150 }
        }
      ];
      edges = [
        { source_node_key: 'start_1', target_node_key: 'agent_research', priority: 1 },
        { source_node_key: 'agent_research', target_node_key: 'transform_1', priority: 1 },
        { source_node_key: 'transform_1', target_node_key: 'end_1', priority: 1 }
      ];
    } else if (templateChoice === 'rag_research') {
      nodes = [
        {
          node_key: 'start_1',
          node_type: 'start',
          name: 'Start Trigger',
          config: { input_schema: { type: 'object' } },
          position: { x: 50, y: 150 }
        },
        {
          node_key: 'rag_retriever',
          node_type: 'rag',
          name: 'RAG Retriever',
          config: { query: '{{input.query}}', top_k: 5 },
          position: { x: 280, y: 150 }
        },
        {
          node_key: 'end_1',
          node_type: 'end',
          name: 'Knowledge Output',
          config: {
            output_template: 'Retrieved {{nodes.rag_retriever.output.documents.length}} evidence passages.'
          },
          position: { x: 520, y: 150 }
        }
      ];
      edges = [
        { source_node_key: 'start_1', target_node_key: 'rag_retriever', priority: 1 },
        { source_node_key: 'rag_retriever', target_node_key: 'end_1', priority: 1 }
      ];
    } else {
      nodes = [
        {
          node_key: 'start_1',
          node_type: 'start',
          name: 'Start Trigger',
          config: { input_schema: { type: 'object' } },
          position: { x: 100, y: 150 }
        },
        {
          node_key: 'end_1',
          node_type: 'end',
          name: 'End Output',
          config: { output_template: 'Workflow executed successfully.' },
          position: { x: 450, y: 150 }
        }
      ];
      edges = [
        { source_node_key: 'start_1', target_node_key: 'end_1', priority: 1 }
      ];
    }

    try {
      const created = await createWorkflow({
        name: newWorkflowName.trim(),
        description: newWorkflowDesc.trim() || 'Automated multi-step processing workflow.',
        nodes,
        edges,
        variables
      });

      success('Workflow Created', `Workflow '${created.name}' initialized.`);
      setShowCreateModal(false);
      setNewWorkflowName('');
      setNewWorkflowDesc('');
      fetchWorkflows();
      navigate(`/user/workflows/${created.id}`);
    } catch (err) {
      console.error('Create workflow error:', err);
      error('Creation Failed', 'Failed to initialize workflow.');
    }
  };

  const handleValidate = async (wId) => {
    try {
      const res = await validateWorkflow(wId);
      setValidationResult(res);
      if (res.valid) {
        success('Validation Passed', 'DAG structure and connectivity are valid.');
      } else {
        warning('Validation Failed', `${res.errors?.length || 0} issues detected.`);
      }
    } catch (err) {
      console.error('Validation error:', err);
      error('Validation Error', 'Unable to validate workflow graph.');
    }
  };

  const handleActivate = async (wId) => {
    try {
      await activateWorkflow(wId);
      success('Workflow Activated', 'Workflow is now live and ready for dispatch.');
      fetchWorkflows();
    } catch (err) {
      console.error('Activate error:', err);
      error('Activation Failed', err.response?.data?.detail || 'Validation error prevented activation.');
    }
  };

  const handlePause = async (wId) => {
    try {
      await pauseWorkflow(wId);
      info('Workflow Paused', 'Workflow dispatch has been temporarily paused.');
      fetchWorkflows();
    } catch (err) {
      console.error('Pause error:', err);
      error('Pause Failed', 'Unable to pause workflow.');
    }
  };

  const handleArchive = async (wId) => {
    try {
      await archiveWorkflow(wId);
      info('Workflow Archived', 'Workflow status set to archived.');
      fetchWorkflows();
    } catch (err) {
      console.error('Archive error:', err);
      error('Archive Failed', 'Unable to archive workflow.');
    }
  };

  const handleConfirmDelete = async () => {
    if (!workflowToDelete) return;
    try {
      await deleteWorkflow(workflowToDelete.id);
      success('Workflow Deleted', `Workflow '${workflowToDelete.name}' removed.`);
      setWorkflowToDelete(null);
      fetchWorkflows();
    } catch (err) {
      console.error('Delete error:', err);
      error('Delete Failed', 'Failed to delete workflow.');
    }
  };

  const handleClone = async (wId) => {
    try {
      const cloned = await cloneWorkflow(wId);
      success('Workflow Cloned', `Created duplicate: ${cloned.name}`);
      fetchWorkflows();
    } catch (err) {
      console.error('Clone error:', err);
      error('Clone Failed', 'Unable to clone workflow.');
    }
  };

  const handleOpenDetail = async (wId) => {
    try {
      const detail = await getWorkflow(wId);
      setSelectedWorkflow(detail);
      const execs = await getWorkflowExecutions(wId);
      setExecutions(execs || []);
      setShowDetailDrawer(true);
    } catch (err) {
      console.error('Get detail error:', err);
      error('Fetch Error', 'Unable to load workflow details.');
    }
  };

  const handleOpenOutline = async (wId) => {
    try {
      const detail = await getWorkflow(wId);
      setSelectedWorkflow(detail);
      setShowOutlineModal(true);
    } catch (err) {
      console.error('Outline error:', err);
    }
  };

  const handleExecute = async () => {
    if (!selectedWorkflow) return;
    try {
      setIsExecuting(true);
      let parsed = {};
      try {
        parsed = JSON.parse(executeInput);
      } catch {
        warning('JSON Syntax Error', 'Execution payload must be valid JSON format.');
        setIsExecuting(false);
        return;
      }

      const res = await executeWorkflow(selectedWorkflow.id, parsed);
      setExecutionResult(res);
      success('Execution Succeeded', `Workflow finished with status: ${res.status}`);
      const updatedExecs = await getWorkflowExecutions(selectedWorkflow.id);
      setExecutions(updatedExecs || []);
    } catch (err) {
      console.error('Execution error:', err);
      error('Execution Failed', err.response?.data?.detail || err.message || 'Execution error.');
    } finally {
      setIsExecuting(false);
    }
  };

  // Filtered & Sorted Workflows
  const filteredWorkflows = useMemo(() => {
    return workflows
      .filter((w) => {
        if (statusFilter !== 'all' && w.status !== statusFilter) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchName = w.name?.toLowerCase().includes(q);
          const matchDesc = (w.description || '').toLowerCase().includes(q);
          if (!matchName && !matchDesc) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        if (sortBy === 'nodes') return (b.node_count || 0) - (a.node_count || 0);
        return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
      });
  }, [workflows, statusFilter, searchQuery, sortBy]);

  // Aggregate KPI Counts
  const kpiStats = useMemo(() => {
    const total = workflows.length;
    const active = workflows.filter((w) => w.status === 'active').length;
    const draft = workflows.filter((w) => w.status === 'draft').length;
    const totalNodes = workflows.reduce((acc, w) => acc + (w.node_count || 0), 0);
    return { total, active, draft, totalNodes };
  }, [workflows]);

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12 font-sans text-slate-200">
      {/* 1. Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/10">
            <WorkflowIcon size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              Workflow Studio
              <Badge variant="indigo">Visual AI Automation</Badge>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Design, connect, validate, schedule, and orchestrate autonomous multi-agent DAG pipelines.
            </p>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchWorkflows}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin text-cyan-400' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2"
          >
            <Plus size={14} />
            New Workflow
          </Button>
        </div>
      </div>

      {/* 2. Overview KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Total Workflows"
          value={kpiStats.total}
          subtitle="Workspace DAG pipelines"
          trend="Authoritative State"
          icon={<WorkflowIcon size={18} className="text-indigo-400" />}
        />
        <MetricCard
          title="Active Automations"
          value={kpiStats.active}
          subtitle="Ready for execution dispatch"
          trend="Validated Graphs"
          icon={<CheckCircle2 size={18} className="text-emerald-400" />}
        />
        <MetricCard
          title="Draft / Paused"
          value={kpiStats.draft}
          subtitle="In design or paused state"
          trend="Safe Editing"
          icon={<SlidersHorizontal size={18} className="text-amber-400" />}
        />
        <MetricCard
          title="Orchestrated Nodes"
          value={kpiStats.totalNodes}
          subtitle="Agents, Tools, Logic & RAG"
          trend="Multi-Domain Cognition"
          icon={<Layers size={18} className="text-cyan-400" />}
        />
      </div>

      {/* 3. Studio Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-3">
        {[
          { id: 'workflows', label: `Workflows Directory (${workflows.length})`, icon: <WorkflowIcon size={14} /> },
          { id: 'approvals', label: 'Pending Approvals', icon: <ShieldCheck size={14} /> },
          { id: 'schedules', label: 'Automation Schedules', icon: <Calendar size={14} /> },
          { id: 'analytics', label: 'Workflow Analytics', icon: <BarChart3 size={14} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:text-white'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 4. Tab Views */}
      {activeTab === 'workflows' && (
        <div className="flex flex-col gap-4">
          {/* Search, Filter & Sort Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search workflows by name or description..."
                className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 pl-10 pr-4 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-[#0d1117] border border-white/10 rounded-md px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="all">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="paused">Paused</option>
                  <option value="archived">Archived</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-[#0d1117] border border-white/10 rounded-md px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="updated">Recently Updated</option>
                  <option value="name">Alphabetical</option>
                  <option value="nodes">Node Count</option>
                </select>
              </div>
            </div>
          </div>

          {/* Workflows List / Grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-48 w-full rounded-xl bg-white/[0.03]" />
              ))}
            </div>
          ) : filteredWorkflows.length === 0 ? (
            <Card className="p-8 text-center">
              <EmptyState
                icon={<WorkflowIcon size={32} className="text-slate-500" />}
                title={searchQuery || statusFilter !== 'all' ? 'No matching workflows found' : 'No Workflows Yet'}
                description={
                  searchQuery || statusFilter !== 'all'
                    ? 'Try adjusting your search criteria or status filters.'
                    : 'Create your first autonomous workflow graph to orchestrate agents, knowledge tools, and tasks.'
                }
                action={
                  <Button variant="primary" size="sm" onClick={() => setShowCreateModal(true)}>
                    <Plus size={14} className="mr-1" /> Create Workflow
                  </Button>
                }
              />
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredWorkflows.map((w) => (
                <Card
                  key={w.id}
                  className="flex flex-col justify-between hover:border-indigo-500/40 transition-all duration-200"
                >
                  <div className="space-y-3">
                    {/* Card Header */}
                    <div className="flex items-start justify-between gap-2 border-b border-white/[0.04] pb-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                          <WorkflowIcon size={15} />
                        </div>
                        <div>
                          <h3 className="font-bold text-xs text-white line-clamp-1">{w.name}</h3>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[10px] font-mono text-slate-500">v{w.version || 1}</span>
                            <span className="text-[10px] text-slate-600">•</span>
                            <span className="text-[10px] text-slate-400">{w.node_count || 0} nodes</span>
                          </div>
                        </div>
                      </div>

                      <StatusBadge
                        status={w.status}
                        label={w.status.toUpperCase()}
                      />
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                      {w.description || 'Automated multi-step processing workflow.'}
                    </p>

                    {/* Metadata strip */}
                    <div className="flex items-center justify-between text-[11px] text-slate-400 bg-black/20 p-2 rounded-lg border border-white/[0.03]">
                      <span>Updated:</span>
                      <span className="font-mono text-slate-300">
                        {w.updated_at ? new Date(w.updated_at).toLocaleDateString() : 'Recently'}
                      </span>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="border-t border-white/[0.04] pt-3 mt-4 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => navigate(`/user/workflows/${w.id}`)}
                        className="text-xs py-1 px-2.5 flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 text-white"
                      >
                        <Edit3 size={11} /> Open Studio
                      </Button>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setSelectedWorkflow(w);
                          setShowExecuteModal(true);
                        }}
                        className="text-xs py-1 px-2 flex items-center gap-1"
                      >
                        <Play size={11} /> Run
                      </Button>
                    </div>

                    <div className="flex items-center gap-1">
                      <IconButton
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenOutline(w.id)}
                        title="Accessible Text Outline"
                        aria-label="Accessible Text Outline"
                      >
                        <FileText size={13} />
                      </IconButton>

                      <IconButton
                        variant="ghost"
                        size="sm"
                        onClick={() => handleClone(w.id)}
                        title="Clone Workflow"
                        aria-label="Clone Workflow"
                      >
                        <Copy size={13} />
                      </IconButton>

                      <IconButton
                        variant="ghost"
                        size="sm"
                        onClick={() => setWorkflowToDelete(w)}
                        title="Delete Workflow"
                        aria-label="Delete Workflow"
                        className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                      >
                        <Trash2 size={13} />
                      </IconButton>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'approvals' && (
        <UserWorkflowApprovals addLog={addLog} triggerNotification={triggerNotification} />
      )}

      {activeTab === 'schedules' && (
        <UserWorkflowSchedules addLog={addLog} triggerNotification={triggerNotification} />
      )}

      {activeTab === 'analytics' && (
        <UserWorkflowAnalytics addLog={addLog} triggerNotification={triggerNotification} />
      )}

      {/* 5. Create Workflow Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Workflow"
        description="Initialize an enterprise visual AI workflow graph in your workspace."
        size="md"
      >
        <form onSubmit={handleCreateWorkflow} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">
              Workflow Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={newWorkflowName}
              onChange={(e) => setNewWorkflowName(e.target.value)}
              placeholder="e.g. Multi-Agent Competitive Intelligence Pipeline"
              required
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Description</label>
            <textarea
              value={newWorkflowDesc}
              onChange={(e) => setNewWorkflowDesc(e.target.value)}
              rows={2}
              placeholder="Describe the workflow purpose, triggers, and expected outcomes..."
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1.5 block">Starter Template</label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {[
                { id: 'agent_pipeline', label: 'Agent Pipeline', desc: 'Agent -> Transform -> End' },
                { id: 'rag_research', label: 'RAG Retriever', desc: 'Vector Search -> Output' },
                { id: 'blank', label: 'Blank Canvas', desc: 'Start -> End empty graph' }
              ].map((tpl) => (
                <button
                  type="button"
                  key={tpl.id}
                  onClick={() => setTemplateChoice(tpl.id)}
                  className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                    templateChoice === tpl.id
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-white'
                      : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold text-xs">{tpl.label}</div>
                  <div className="text-[10px] text-slate-400 mt-1">{tpl.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white">
              Initialize & Open Studio
            </Button>
          </div>
        </form>
      </Modal>

      {/* 6. Run Execution Modal */}
      <Modal
        isOpen={showExecuteModal}
        onClose={() => {
          setShowExecuteModal(false);
          setExecutionResult(null);
        }}
        title={`Execute Workflow: ${selectedWorkflow?.name || ''}`}
        description="Dispatch asynchronous or synchronous DAG execution with custom input parameters."
        size="lg"
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">
              Input Payload (JSON)
            </label>
            <textarea
              value={executeInput}
              onChange={(e) => setExecuteInput(e.target.value)}
              rows={5}
              className="w-full bg-[#0d1117] border border-white/10 rounded-lg p-3 font-mono text-xs text-indigo-300 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          {executionResult && (
            <div className="p-3.5 rounded-lg bg-black/40 border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 size={14} /> Execution Status: {executionResult.status}
                </span>
                <span className="text-[10px] font-mono text-slate-500">ID: {executionResult.id}</span>
              </div>
              <pre className="text-xs text-slate-300 bg-black/50 p-2.5 rounded font-mono overflow-x-auto max-h-48">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setShowExecuteModal(false);
                setExecutionResult(null);
              }}
            >
              Close
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleExecute}
              disabled={isExecuting}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              <Play size={13} className={isExecuting ? 'animate-spin' : ''} />
              {isExecuting ? 'Dispatching...' : 'Dispatch Execution'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* 7. Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(workflowToDelete)}
        onClose={() => setWorkflowToDelete(null)}
        title="Delete Workflow"
        description="Are you sure you want to permanently delete this workflow? This action cannot be undone."
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200">
            Deleting <span className="font-bold text-white">'{workflowToDelete?.name}'</span> will remove all attached graph definitions, schedules, and variable bindings from the workspace.
          </div>
          <div className="flex items-center justify-end gap-2.5 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setWorkflowToDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" onClick={handleConfirmDelete}>
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>

      {/* 8. Accessible Plain-Text Outline Modal */}
      <Modal
        isOpen={showOutlineModal}
        onClose={() => setShowOutlineModal(false)}
        title={`Accessible Workflow Outline: ${selectedWorkflow?.name || ''}`}
        description="Linear text-based breakdown of graph nodes, edges, and dependencies for screen readers and linear review."
        size="md"
      >
        <div className="space-y-3">
          <div className="text-xs text-slate-300 space-y-2 max-h-80 overflow-y-auto pr-1">
            {(selectedWorkflow?.nodes || []).map((node, idx) => {
              const outEdges = (selectedWorkflow?.edges || []).filter((e) => e.source_node_id === node.id);
              return (
                <div key={node.id || idx} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {idx + 1}. {node.name} ({node.node_type})
                    </span>
                    <Badge variant="slate">{node.node_key}</Badge>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Type: <span className="text-indigo-300 font-mono">{node.node_type}</span>
                  </p>
                  {outEdges.length > 0 && (
                    <div className="text-[11px] text-slate-400 mt-1">
                      → Connects to:{' '}
                      {outEdges
                        .map((e) => {
                          const target = (selectedWorkflow?.nodes || []).find((n) => n.id === e.target_node_id);
                          return target ? target.name : e.target_node_id;
                        })
                        .join(', ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex justify-end pt-3 border-t border-white/[0.06]">
            <Button variant="secondary" size="sm" onClick={() => setShowOutlineModal(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
