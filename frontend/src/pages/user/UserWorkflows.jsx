import React, { useState, useEffect } from 'react';
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
  FileCode
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
  getWorkflowExecutions
} from '../../api/workflows';

export default function UserWorkflows({ addLog, triggerNotification }) {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [executions, setExecutions] = useState([]);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Form states
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');
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
      if (addLog) addLog('Workflows', 'Failed to fetch workflows from backend.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const handleCreateSampleWorkflow = async () => {
    if (!newWorkflowName.trim()) return;
    try {
      const samplePayload = {
        name: newWorkflowName.trim(),
        description: newWorkflowDesc.trim() || 'Automated multi-step processing workflow.',
        nodes: [
          {
            node_key: 'start_1',
            node_type: 'start',
            name: 'Start Trigger',
            config: { input_schema: { type: 'object' } },
            position: { x: 50, y: 150 }
          },
          {
            node_key: 'transform_1',
            node_type: 'transform',
            name: 'Data Formatter',
            config: {
              mapping: {
                greeting: '{{input.message}}',
                project: '{{variables.env_name}}',
                received_at: '{{input.count}}'
              }
            },
            position: { x: 250, y: 150 }
          },
          {
            node_key: 'end_1',
            node_type: 'end',
            name: 'Final Output',
            config: {
              output_template: 'Processed successfully: {{nodes.transform_1.output.transformed.greeting}}'
            },
            position: { x: 450, y: 150 }
          }
        ],
        edges: [
          { source_node_key: 'start_1', target_node_key: 'transform_1', priority: 1 },
          { source_node_key: 'transform_1', target_node_key: 'end_1', priority: 1 }
        ],
        variables: [
          { name: 'env_name', value: 'Production', value_type: 'string', is_secret: false }
        ]
      };

      const created = await createWorkflow(samplePayload);
      if (triggerNotification) triggerNotification('Workflow Created', `Workflow '${created.name}' initialized.`);
      setShowCreateModal(false);
      setNewWorkflowName('');
      setNewWorkflowDesc('');
      fetchWorkflows();
    } catch (err) {
      console.error('Create workflow error:', err);
      if (triggerNotification) triggerNotification('Error', 'Failed to create workflow.');
    }
  };

  const handleValidate = async (wId) => {
    try {
      const res = await validateWorkflow(wId);
      setValidationResult(res);
      if (res.valid) {
        if (triggerNotification) triggerNotification('Validation Passed', 'DAG structure is valid.');
      } else {
        if (triggerNotification) triggerNotification('Validation Failed', `${res.errors.length} errors found.`);
      }
    } catch (err) {
      console.error('Validation error:', err);
    }
  };

  const handleActivate = async (wId) => {
    try {
      await activateWorkflow(wId);
      if (triggerNotification) triggerNotification('Workflow Activated', 'Ready for live execution.');
      fetchWorkflows();
    } catch (err) {
      console.error('Activate error:', err);
      if (triggerNotification) triggerNotification('Activation Failed', err.response?.data?.detail || 'Validation error');
    }
  };

  const handlePause = async (wId) => {
    try {
      await pauseWorkflow(wId);
      if (triggerNotification) triggerNotification('Workflow Paused', 'Execution paused.');
      fetchWorkflows();
    } catch (err) {
      console.error('Pause error:', err);
    }
  };

  const handleArchive = async (wId) => {
    try {
      await archiveWorkflow(wId);
      if (triggerNotification) triggerNotification('Workflow Archived', 'Status set to archived.');
      fetchWorkflows();
    } catch (err) {
      console.error('Archive error:', err);
    }
  };

  const handleDelete = async (wId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await deleteWorkflow(wId);
      if (triggerNotification) triggerNotification('Workflow Deleted', 'Removed from workspace.');
      fetchWorkflows();
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleOpenDetail = async (wId) => {
    try {
      const detail = await getWorkflow(wId);
      setSelectedWorkflow(detail);
      const execs = await getWorkflowExecutions(wId);
      setExecutions(execs || []);
      setShowDetailModal(true);
    } catch (err) {
      console.error('Get detail error:', err);
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
        alert('Invalid JSON input format.');
        setIsExecuting(false);
        return;
      }

      const res = await executeWorkflow(selectedWorkflow.id, parsed);
      setExecutionResult(res);
      if (triggerNotification) triggerNotification('Execution Completed', `Status: ${res.status}`);
      const updatedExecs = await getWorkflowExecutions(selectedWorkflow.id);
      setExecutions(updatedExecs || []);
    } catch (err) {
      console.error('Execution error:', err);
      if (triggerNotification) triggerNotification('Execution Failed', err.response?.data?.detail || 'Error');
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <WorkflowIcon className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Workflow Engine</h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Phase 7.1 Foundation
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Design, validate, version, and execute automated multi-node DAG workflows.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchWorkflows}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-600/20 transition"
          >
            <Plus className="w-4 h-4" />
            New Workflow
          </button>
        </div>
      </div>

      {/* Validation Banner if active */}
      {validationResult && (
        <div className={`p-4 rounded-xl border ${validationResult.valid ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300' : 'bg-rose-950/30 border-rose-800/40 text-rose-300'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {validationResult.valid ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
              <span className="font-semibold">{validationResult.valid ? 'DAG Validation Passed' : 'DAG Validation Errors Detected'}</span>
            </div>
            <button onClick={() => setValidationResult(null)} className="text-slate-400 hover:text-slate-200">
              <X className="w-4 h-4" />
            </button>
          </div>
          {validationResult.errors?.length > 0 && (
            <ul className="mt-2 text-xs space-y-1 list-disc list-inside text-rose-400">
              {validationResult.errors.map((e, idx) => (
                <li key={idx}><strong>{e.code}:</strong> {e.message}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Workflows List */}
      {loading ? (
        <div className="text-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-400" />
          Loading workflows...
        </div>
      ) : workflows.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800/60 p-8">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-4 text-indigo-400">
            <WorkflowIcon className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold text-slate-200 mb-1">No Workflows Configured</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-6">
            Get started by initializing a standard DAG workflow template with Start, Transform, and End nodes.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg transition"
          >
            Create First Workflow
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workflows.map((w) => (
            <div
              key={w.id}
              className="bg-slate-900/70 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 flex flex-col justify-between transition group shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-md uppercase tracking-wider ${
                      w.status === 'active'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : w.status === 'paused'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}>
                      {w.status}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">v{w.version}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleValidate(w.id)}
                      title="Validate DAG"
                      className="p-1.5 text-slate-400 hover:text-indigo-400 rounded-lg hover:bg-slate-800 transition"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(w.id)}
                      title="Delete Workflow"
                      className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <h3 className="text-lg font-semibold text-slate-200 mb-1 group-hover:text-indigo-300 transition">
                  {w.name}
                </h3>
                <p className="text-xs text-slate-400 line-clamp-2 mb-4">
                  {w.description || 'No description provided.'}
                </p>

                <div className="flex items-center gap-4 text-xs text-slate-400 mb-4 py-2 px-3 bg-slate-950/40 rounded-xl border border-slate-800/60 font-mono">
                  <span className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    {w.node_count} Nodes
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-cyan-400" />
                    {w.edge_count} Edges
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-slate-800/80">
                <button
                  onClick={() => handleOpenDetail(w.id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Inspect
                </button>

                {w.status === 'active' ? (
                  <button
                    onClick={() => handlePause(w.id)}
                    className="py-1.5 px-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 text-xs font-medium transition"
                  >
                    <Pause className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleActivate(w.id)}
                    className="py-1.5 px-3 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/20 text-xs font-medium transition"
                  >
                    <Play className="w-3.5 h-3.5" />
                  </button>
                )}

                <button
                  onClick={() => {
                    setSelectedWorkflow(w);
                    setExecutionResult(null);
                    setShowExecuteModal(true);
                  }}
                  className="py-1.5 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-sm transition"
                >
                  Execute
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Plus className="w-5 h-5 text-indigo-400" />
              Create Standard Workflow
            </h3>
            <p className="text-xs text-slate-400">
              Creates a starter DAG template with a Start Trigger, Data Transform Node, and Output Node.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Workflow Name</label>
                <input
                  type="text"
                  placeholder="e.g. Lead Qualification Pipeline"
                  value={newWorkflowName}
                  onChange={(e) => setNewWorkflowName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Description</label>
                <textarea
                  placeholder="Summarize workflow purpose..."
                  value={newWorkflowDesc}
                  onChange={(e) => setNewWorkflowDesc(e.target.value)}
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3.5 py-1.5 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSampleWorkflow}
                disabled={!newWorkflowName.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium transition"
              >
                Create Workflow
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Execute Modal */}
      {showExecuteModal && selectedWorkflow && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Play className="w-5 h-5 text-indigo-400" />
                Execute Workflow: {selectedWorkflow.name}
              </h3>
              <button onClick={() => setShowExecuteModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Input Data (JSON)</label>
              <textarea
                value={executeInput}
                onChange={(e) => setExecuteInput(e.target.value)}
                rows={5}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-indigo-300 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {executionResult && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Execution Output</span>
                  <span className={`px-2 py-0.5 rounded font-mono ${executionResult.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                    {executionResult.status}
                  </span>
                </div>
                <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto max-h-48">
                  {JSON.stringify(executionResult.output_data || executionResult.error, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowExecuteModal(false)}
                className="px-3.5 py-1.5 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-medium"
              >
                Close
              </button>
              <button
                onClick={handleExecute}
                disabled={isExecuting}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium transition"
              >
                {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Run Workflow
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Detail Modal */}
      {showDetailModal && selectedWorkflow && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col p-6 shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-xl font-bold text-slate-100">{selectedWorkflow.name}</h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">Version {selectedWorkflow.version} • Status: {selectedWorkflow.status}</p>
              </div>
              <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-6">
              {/* Nodes Summary */}
              <div>
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  Nodes ({selectedWorkflow.nodes?.length || 0})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {selectedWorkflow.nodes?.map((n) => (
                    <div key={n.id} className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-slate-200">{n.name}</span>
                        <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono text-[10px] uppercase">
                          {n.node_type}
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono block text-[11px]">key: {n.node_key}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Execution History */}
              <div>
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  Recent Executions ({executions.length})
                </h4>
                {executions.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No executions recorded yet.</p>
                ) : (
                  <div className="space-y-2">
                    {executions.slice(0, 5).map((ex) => (
                      <div key={ex.id} className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded font-mono text-[10px] ${ex.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {ex.status}
                          </span>
                          <span className="text-slate-400 font-mono">{ex.id.slice(0, 8)}...</span>
                        </div>
                        <span className="text-slate-500 text-[11px]">
                          {new Date(ex.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium"
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
