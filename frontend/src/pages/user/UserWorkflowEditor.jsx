import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  ReactFlowProvider
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import WorkflowNodeComponent from '../../components/workflow/WorkflowNode';
import WorkflowNodePalette from '../../components/workflow/WorkflowNodePalette';
import WorkflowNodeEditor from '../../components/workflow/WorkflowNodeEditor';
import WorkflowEdgeEditor from '../../components/workflow/WorkflowEdgeEditor';
import WorkflowVariablesPanel from '../../components/workflow/WorkflowVariablesPanel';
import WorkflowToolbar from '../../components/workflow/WorkflowToolbar';
import WorkflowValidationPanel from '../../components/workflow/WorkflowValidationPanel';

import {
  getWorkflowDefinition,
  updateWorkflowDefinition,
  validateWorkflow,
  activateWorkflow,
  pauseWorkflow,
  executeWorkflow,
  getWorkflowExecutions,
  getWorkflowExecution,
  cancelWorkflowExecution,
  approveWorkflowExecution,
  cloneWorkflow
} from '../../api/workflows';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import {
  Button,
  IconButton,
  Badge,
  StatusBadge,
  Modal,
  Drawer,
  Skeleton
} from '../../components/ui';

import {
  Play,
  RefreshCw,
  X,
  AlertCircle,
  Clock,
  CheckCircle2,
  AlertTriangle,
  History,
  StopCircle,
  Check,
  ChevronRight,
  FileText,
  Copy,
  Layers,
  Shield
} from 'lucide-react';

const nodeTypes = {
  workflowNode: WorkflowNodeComponent
};

function WorkflowEditorContent({ triggerNotification, addLog }) {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const { success, error, warning, info } = useToast();

  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [variables, setVariables] = useState([]);

  // Selection states
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);

  // Panels & Modals
  const [showVariablesModal, setShowVariablesModal] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [showRunModal, setShowRunModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showOutlineModal, setShowOutlineModal] = useState(false);
  const [runInput, setRunInput] = useState('{\n  "message": "Hello AegisAI Workflow"\n}');

  // Execution state
  const [activeExecution, setActiveExecution] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  // History for Undo/Redo
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const pushHistory = useCallback((newNodes, newEdges, newVars) => {
    setHistory((prev) => {
      const next = prev.slice(0, historyIndex + 1);
      return [...next, { nodes: newNodes, edges: newEdges, variables: newVars }];
    });
    setHistoryIndex((prev) => prev + 1);
    setIsDirty(true);
  }, [historyIndex]);

  // 1. Fetch Workflow Definition
  const loadWorkflow = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getWorkflowDefinition(workflowId);
      setWorkflow(data);
      setVariables(data.variables || []);

      const rfNodes = (data.nodes || []).map((n) => ({
        id: n.id,
        type: 'workflowNode',
        position: n.position || { x: 100, y: 100 },
        data: {
          name: n.name,
          node_key: n.node_key,
          node_type: n.node_type,
          config: n.config || {},
          is_enabled: n.is_enabled !== false,
          executionStatus: null,
          onDelete: (id) => handleDeleteNode(id)
        }
      }));

      const rfEdges = (data.edges || []).map((e) => ({
        id: e.id,
        source: e.source_node_id,
        target: e.target_node_id,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#818cf8' },
        style: { stroke: '#818cf8', strokeWidth: 2 },
        data: {
          priority: e.priority || 1,
          condition: e.condition || null
        }
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
      setHistory([{ nodes: rfNodes, edges: rfEdges, variables: data.variables || [] }]);
      setHistoryIndex(0);
      setIsDirty(false);
    } catch (err) {
      console.error('Failed to load workflow definition:', err);
      error('Load Error', 'Failed to load workflow definition.');
      if (triggerNotification) triggerNotification('Error', 'Failed to load workflow definition.');
    } finally {
      setLoading(false);
    }
  }, [workflowId, triggerNotification]);

  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  // 2. Sync Execution status to node graph
  const syncExecutionToNodes = useCallback((exec) => {
    if (!exec) return;
    setActiveExecution(exec);

    const statusMap = {};
    (exec.execution_nodes || []).forEach((en) => {
      statusMap[en.node_key] = en.status?.toLowerCase();
    });

    setNodes((prevNodes) =>
      prevNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          executionStatus: statusMap[n.data.node_key] || null
        }
      }))
    );
  }, [setNodes]);

  // 3. Drag and Drop Node Addition
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleAddNode = useCallback((nodeType, pos = null) => {
    if (!reactFlowInstance) return;

    const existingKeys = new Set(nodes.map((n) => n.data.node_key));
    let suffix = 1;
    while (existingKeys.has(`${nodeType}_${suffix}`)) {
      suffix += 1;
    }
    const nodeKey = `${nodeType}_${suffix}`;

    let position = pos;
    if (!position) {
      const center = reactFlowInstance.screenToFlowPosition({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
      });
      position = center;
    }

    const newNodeId = `node_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    const newNode = {
      id: newNodeId,
      type: 'workflowNode',
      position,
      data: {
        name: `${nodeType.toUpperCase()} Node`,
        node_key: nodeKey,
        node_type: nodeType,
        config: {},
        is_enabled: true,
        executionStatus: null,
        onDelete: (id) => handleDeleteNode(id)
      }
    };

    const nextNodes = [...nodes, newNode];
    setNodes(nextNodes);
    setSelectedNodeId(newNodeId);
    setSelectedEdgeId(null);
    pushHistory(nextNodes, edges, variables);
  }, [reactFlowInstance, nodes, edges, variables, pushHistory]);

  const onDrop = useCallback((event) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/reactflow/type');
    if (!type || !reactFlowInstance) return;

    const position = reactFlowInstance.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY
    });

    handleAddNode(type, position);
  }, [reactFlowInstance, handleAddNode]);

  // 4. Connect Edges
  const onConnect = useCallback((params) => {
    if (params.source === params.target) {
      warning('Invalid Connection', 'Self-loops are not permitted in DAG architectures.');
      return;
    }

    const duplicate = edges.some(
      (e) => e.source === params.source && e.target === params.target
    );
    if (duplicate) {
      warning('Duplicate Connection', 'An edge already connects these two nodes.');
      return;
    }

    const newEdge = {
      ...params,
      id: `edge_${Date.now()}`,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#818cf8' },
      style: { stroke: '#818cf8', strokeWidth: 2 },
      data: { priority: 1, condition: null }
    };

    const nextEdges = addEdge(newEdge, edges);
    setEdges(nextEdges);
    pushHistory(nodes, nextEdges, variables);
  }, [edges, nodes, variables, pushHistory, warning]);

  // 5. Update Node
  const handleUpdateNode = useCallback((id, updatedData) => {
    const nextNodes = nodes.map((n) => {
      if (n.id === id) {
        return { ...n, data: updatedData };
      }
      return n;
    });
    setNodes(nextNodes);
    pushHistory(nextNodes, edges, variables);
  }, [nodes, edges, variables, pushHistory]);

  // 6. Delete Node
  const handleDeleteNode = useCallback((id) => {
    const nextNodes = nodes.filter((n) => n.id !== id);
    const nextEdges = edges.filter((e) => e.source !== id && e.target !== id);
    setNodes(nextNodes);
    setEdges(nextEdges);
    if (selectedNodeId === id) setSelectedNodeId(null);
    pushHistory(nextNodes, nextEdges, variables);
  }, [nodes, edges, variables, selectedNodeId, pushHistory]);

  // 7. Update Edge
  const handleUpdateEdge = useCallback((id, updatedData) => {
    const nextEdges = edges.map((e) => {
      if (e.id === id) {
        return { ...e, data: updatedData };
      }
      return e;
    });
    setEdges(nextEdges);
    pushHistory(nodes, nextEdges, variables);
  }, [edges, nodes, variables, pushHistory]);

  // 8. Delete Edge
  const handleDeleteEdge = useCallback((id) => {
    const nextEdges = edges.filter((e) => e.id !== id);
    setEdges(nextEdges);
    if (selectedEdgeId === id) setSelectedEdgeId(null);
    pushHistory(nodes, nextEdges, variables);
  }, [edges, nodes, variables, selectedEdgeId, pushHistory]);

  // 9. Variables Update
  const handleVariablesChange = useCallback((newVars) => {
    setVariables(newVars);
    pushHistory(nodes, edges, newVars);
  }, [nodes, edges, pushHistory]);

  // 10. Undo / Redo
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const prev = history[historyIndex - 1];
      setNodes(prev.nodes);
      setEdges(prev.edges);
      setVariables(prev.variables);
      setHistoryIndex(historyIndex - 1);
      setIsDirty(true);
    }
  }, [history, historyIndex]);

  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const next = history[historyIndex + 1];
      setNodes(next.nodes);
      setEdges(next.edges);
      setVariables(next.variables);
      setHistoryIndex(historyIndex + 1);
      setIsDirty(true);
    }
  }, [history, historyIndex]);

  // 11. Auto-Layout
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;

    const adj = {};
    const inDegree = {};
    nodes.forEach((n) => {
      adj[n.id] = [];
      inDegree[n.id] = 0;
    });

    edges.forEach((e) => {
      if (adj[e.source] && inDegree[e.target] !== undefined) {
        adj[e.source].push(e.target);
        inDegree[e.target] += 1;
      }
    });

    const levels = {};
    const queue = [];
    nodes.forEach((n) => {
      if (inDegree[n.id] === 0) {
        queue.push({ id: n.id, level: 0 });
        levels[n.id] = 0;
      }
    });

    while (queue.length > 0) {
      const { id, level } = queue.shift();
      (adj[id] || []).forEach((tgt) => {
        const nextLevel = Math.max(level + 1, levels[tgt] || 0);
        levels[tgt] = nextLevel;
        queue.push({ id: tgt, level: nextLevel });
      });
    }

    const levelBuckets = {};
    nodes.forEach((n) => {
      const lvl = levels[n.id] || 0;
      if (!levelBuckets[lvl]) levelBuckets[lvl] = [];
      levelBuckets[lvl].push(n.id);
    });

    const nextNodes = nodes.map((n) => {
      const lvl = levels[n.id] || 0;
      const bucket = levelBuckets[lvl] || [];
      const bucketIdx = bucket.indexOf(n.id);
      return {
        ...n,
        position: {
          x: 100 + lvl * 320,
          y: 100 + bucketIdx * 150
        }
      };
    });

    setNodes(nextNodes);
    pushHistory(nextNodes, edges, variables);
    setTimeout(() => {
      if (reactFlowInstance) reactFlowInstance.fitView({ padding: 0.2 });
    }, 50);
  }, [nodes, edges, variables, pushHistory, reactFlowInstance]);

  // 12. Save Workflow Definition
  const handleSave = async () => {
    if (!workflow) return;
    try {
      setIsSaving(true);

      const payloadNodes = nodes.map((n) => ({
        node_key: n.data.node_key,
        node_type: n.data.node_type,
        name: n.data.name,
        config: n.data.config || {},
        position: n.position,
        is_enabled: n.data.is_enabled !== false
      }));

      const payloadEdges = edges.map((e) => {
        const srcNode = nodes.find((n) => n.id === e.source);
        const tgtNode = nodes.find((n) => n.id === e.target);
        return {
          source_node_key: srcNode?.data?.node_key,
          target_node_key: tgtNode?.data?.node_key,
          priority: e.data?.priority || 1,
          condition: e.data?.condition || null
        };
      });

      const payload = {
        expected_version: workflow.version,
        name: workflow.name,
        description: workflow.description,
        nodes: payloadNodes,
        edges: payloadEdges,
        variables: variables.map((v) => ({
          name: v.name,
          value: v.value,
          value_type: v.value_type || 'string',
          is_secret: v.is_secret || false
        }))
      };

      const updated = await updateWorkflowDefinition(workflow.id, payload);
      setWorkflow(updated);
      setIsDirty(false);
      success('Workflow Saved', `Saved version ${updated.version} successfully.`);
    } catch (err) {
      console.error('Save failed:', err);
      if (err.status === 409) {
        warning('Version Conflict', 'Workflow was modified by another session. Please reload the latest definition before saving.');
      } else {
        error('Save Failed', err.message || 'Validation error');
      }
    } finally {
      setIsSaving(false);
    }
  };

  // 13. Validate
  const handleValidate = async () => {
    if (!workflow) return;
    try {
      setIsValidating(true);
      const res = await validateWorkflow(workflow.id);
      setValidationResult(res);
      if (res.valid) {
        success('Validation Passed', 'Graph topology and connectivity are valid.');
      } else {
        warning('Validation Warning', `Detected ${res.errors?.length || 0} issues.`);
      }
    } catch (err) {
      console.error('Validation error:', err);
      error('Validation Error', 'Failed to validate workflow.');
    } finally {
      setIsValidating(false);
    }
  };

  // 14. Status Toggle
  const handleToggleStatus = async () => {
    if (!workflow) return;
    try {
      if (workflow.status === 'active') {
        const updated = await pauseWorkflow(workflow.id);
        setWorkflow(updated);
        info('Workflow Paused', 'Workflow dispatch has been paused.');
      } else {
        const updated = await activateWorkflow(workflow.id);
        setWorkflow(updated);
        success('Workflow Activated', 'Workflow is now live and ready for dispatch.');
      }
    } catch (err) {
      console.error('Status toggle failed:', err);
      error('Status Update Failed', err.message || 'Cannot activate invalid workflow');
    }
  };

  // 15. Execute Run
  const handleRun = async () => {
    if (!workflow) return;
    try {
      setIsRunning(true);
      let parsed = {};
      try {
        parsed = JSON.parse(runInput);
      } catch {
        warning('JSON Syntax Error', 'Execution arguments must be valid JSON.');
        setIsRunning(false);
        return;
      }
      const res = await executeWorkflow(workflow.id, parsed);
      syncExecutionToNodes(res);
      success('Execution Started', `Workflow execution dispatched with status: ${res.status}`);
    } catch (err) {
      console.error('Run failed:', err);
      error('Execution Failed', err.message || 'Execution error');
    } finally {
      setIsRunning(false);
    }
  };

  // 16. Approve Waiting Execution
  const handleApprove = async (approved = true) => {
    if (!activeExecution) return;
    try {
      setIsApproving(true);
      const res = await approveWorkflowExecution(activeExecution.id, approved);
      const detailed = await getWorkflowExecution(res.id);
      syncExecutionToNodes(detailed);
      success('Decision Recorded', `Execution is now ${res.status}`);
    } catch (err) {
      console.error('Approval failed:', err);
      error('Approval Error', err.message);
    } finally {
      setIsApproving(false);
    }
  };

  // 17. Cancel Running Execution
  const handleCancelExecution = async () => {
    if (!activeExecution) return;
    try {
      const res = await cancelWorkflowExecution(activeExecution.id);
      const detailed = await getWorkflowExecution(res.id);
      syncExecutionToNodes(detailed);
      info('Execution Cancelled', 'Execution was aborted by operator.');
    } catch (err) {
      console.error('Cancel failed:', err);
      error('Cancellation Error', 'Unable to abort execution.');
    }
  };

  // 18. Load Execution History
  const handleOpenHistory = async () => {
    try {
      const list = await getWorkflowExecutions(workflow.id, { limit: 20 });
      setExecutions(list || []);
      setShowHistoryModal(true);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleSelectHistoryExecution = async (execId) => {
    try {
      const detailed = await getWorkflowExecution(execId);
      syncExecutionToNodes(detailed);
      setShowHistoryModal(false);
      setShowRunModal(true);
    } catch (err) {
      console.error('Failed to get execution detail:', err);
    }
  };

  if (loading) {
    return (
      <div className="h-screen bg-[#07080a] flex flex-col items-center justify-center text-slate-400 gap-3 font-sans">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
        <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Loading Workflow Canvas...</span>
      </div>
    );
  }

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId);
  const hasStartNode = nodes.some((n) => n.data?.node_type === 'start');

  // Selected node execution data if available
  const selectedNodeExec = activeExecution?.execution_nodes?.find(
    (en) => en.node_key === selectedNode?.data?.node_key
  );

  return (
    <div className="h-screen w-full flex flex-col bg-[#07080a] text-slate-100 overflow-hidden font-sans">
      {/* Top Toolbar */}
      <WorkflowToolbar
        workflow={workflow}
        isDirty={isDirty}
        isSaving={isSaving}
        isValidating={isValidating}
        validationResult={validationResult}
        onSave={handleSave}
        onValidate={handleValidate}
        onToggleStatus={handleToggleStatus}
        onOpenVariables={() => setShowVariablesModal(true)}
        onAutoLayout={handleAutoLayout}
        onUndo={handleUndo}
        onRedo={handleRedo}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
        onFitView={() => reactFlowInstance && reactFlowInstance.fitView({ padding: 0.2 })}
        onRunWorkflow={() => setShowRunModal(true)}
        onOpenOutline={() => setShowOutlineModal(true)}
        onCloneWorkflow={async () => {
          const cloned = await cloneWorkflow(workflow.id);
          navigate(`/user/workflows/${cloned.id}`);
        }}
        onUpdateMetadata={(meta) => {
          setWorkflow((prev) => ({ ...prev, ...meta }));
          setIsDirty(true);
        }}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex overflow-hidden relative" ref={reactFlowWrapper}>
        {/* Left: Node Palette */}
        <WorkflowNodePalette
          onAddNode={(type) => handleAddNode(type)}
          hasStartNode={hasStartNode}
        />

        {/* Center: React Flow Canvas */}
        <div className="flex-1 h-full bg-[#050608] relative">
          {/* Active Execution Banner */}
          {activeExecution && (
            <div className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/95 border border-white/10 p-2.5 rounded-2xl backdrop-blur-xl shadow-xl select-none">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-slate-400">Execution:</span>
                <span className="text-xs font-mono text-indigo-300 font-bold">
                  {activeExecution.id.slice(0, 8)}...
                </span>
                <StatusBadge status={activeExecution.status} label={activeExecution.status.toUpperCase()} />
              </div>

              {activeExecution.status === 'waiting_approval' && (
                <div className="flex items-center gap-1.5 ml-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleApprove(true)}
                    disabled={isApproving}
                    className="text-xs py-1 px-2 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    <Check className="w-3 h-3" /> Approve
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleApprove(false)}
                    disabled={isApproving}
                    className="text-xs py-1 px-2"
                  >
                    <X className="w-3 h-3" /> Reject
                  </Button>
                </div>
              )}

              {activeExecution.status === 'running' && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleCancelExecution}
                  className="text-xs py-1 px-2"
                >
                  <StopCircle className="w-3 h-3" /> Cancel
                </Button>
              )}

              <IconButton
                variant="ghost"
                size="sm"
                onClick={handleOpenHistory}
                title="Execution History"
                aria-label="Execution History"
              >
                <History className="w-3.5 h-3.5 text-slate-400" />
              </IconButton>
            </div>
          )}

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id);
              setSelectedEdgeId(null);
            }}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(edge.id);
              setSelectedNodeId(null);
            }}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            }}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#818cf8', strokeWidth: 2 }
            }}
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="!bg-slate-900 !border-slate-800 !text-slate-300" />
            <MiniMap
              nodeColor={(n) => {
                if (n.data?.executionStatus === 'completed') return '#10b981';
                if (n.data?.executionStatus === 'failed') return '#f43f5e';
                if (n.data?.executionStatus === 'running') return '#818cf8';
                if (n.data?.node_type === 'start') return '#10b981';
                if (n.data?.node_type === 'end') return '#f43f5e';
                return '#6366f1';
              }}
              className="!bg-slate-950/80 !border-slate-800 !rounded-xl overflow-hidden"
            />
          </ReactFlow>
        </div>

        {/* Right: Node / Execution Inspector Drawer */}
        {selectedNode && (
          <div className="w-96 bg-[#0a0c10] border-l border-white/[0.08] h-full flex flex-col z-20 shadow-2xl">
            {selectedNodeExec ? (
              <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">Execution Node Output</span>
                    <StatusBadge status={selectedNodeExec.status} label={selectedNodeExec.status} />
                  </div>
                  <IconButton
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedNodeId(null)}
                    aria-label="Close Inspector"
                  >
                    <X size={14} />
                  </IconButton>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Node Key</span>
                  <div className="font-mono text-slate-200 bg-black/40 p-2 rounded-lg border border-white/[0.04]">
                    {selectedNodeExec.node_key}
                  </div>
                </div>

                {selectedNodeExec.error && (
                  <div>
                    <span className="text-rose-400 text-[10px] uppercase font-bold block mb-1">Error</span>
                    <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 font-mono">
                      {selectedNodeExec.error}
                    </div>
                  </div>
                )}

                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Output Data</span>
                  <pre className="p-3 rounded-xl bg-black/50 border border-white/[0.06] font-mono text-emerald-400 overflow-x-auto max-h-64 text-xs">
                    {JSON.stringify(selectedNodeExec.output_data, null, 2)}
                  </pre>
                </div>

                <div className="pt-2 border-t border-white/[0.06] flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => syncExecutionToNodes(null)}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    Edit Node Config &rarr;
                  </Button>
                </div>
              </div>
            ) : (
              <WorkflowNodeEditor
                selectedNode={selectedNode}
                allNodes={nodes}
                onUpdateNode={handleUpdateNode}
                onDeleteNode={handleDeleteNode}
                onClose={() => setSelectedNodeId(null)}
              />
            )}
          </div>
        )}

        {selectedEdge && (
          <WorkflowEdgeEditor
            selectedEdge={selectedEdge}
            allNodes={nodes}
            onUpdateEdge={handleUpdateEdge}
            onDeleteEdge={handleDeleteEdge}
            onClose={() => setSelectedEdgeId(null)}
          />
        )}
      </div>

      {/* Validation Panel */}
      <WorkflowValidationPanel
        validationResult={validationResult}
        onFocusNode={(nodeKey) => {
          const target = nodes.find((n) => n.data?.node_key === nodeKey);
          if (target && reactFlowInstance) {
            reactFlowInstance.setCenter(target.position.x + 100, target.position.y + 50, { zoom: 1.2, duration: 800 });
            setSelectedNodeId(target.id);
          }
        }}
        onClose={() => setValidationResult(null)}
      />

      {/* Variables Modal */}
      {showVariablesModal && (
        <WorkflowVariablesPanel
          variables={variables}
          onChangeVariables={handleVariablesChange}
          onClose={() => setShowVariablesModal(false)}
        />
      )}

      {/* Run Execution Modal */}
      <Modal
        isOpen={showRunModal}
        onClose={() => setShowRunModal(false)}
        title={`Execute Workflow: ${workflow?.name || ''}`}
        description="Dispatch DAG execution with input arguments."
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Input Parameters (JSON)</label>
            <textarea
              value={runInput}
              onChange={(e) => setRunInput(e.target.value)}
              rows={5}
              className="w-full bg-[#0d1117] border border-white/10 rounded-xl p-3 font-mono text-xs text-indigo-300 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          {activeExecution && (
            <div className="p-3.5 rounded-lg bg-black/40 border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300">Execution Output</span>
                <StatusBadge status={activeExecution.status} label={activeExecution.status.toUpperCase()} />
              </div>
              <pre className="p-3 rounded-lg bg-black/50 border border-white/[0.04] text-xs font-mono text-emerald-400 overflow-x-auto max-h-48">
                {JSON.stringify(activeExecution.output_data || activeExecution.error, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <Button variant="secondary" size="sm" onClick={() => setShowRunModal(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white"
            >
              <Play size={13} className={isRunning ? 'animate-spin' : ''} />
              {isRunning ? 'Dispatching...' : 'Dispatch Execution'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Execution History Modal */}
      <Modal
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        title="Execution History"
        description="Review previous execution runs and inspect outputs."
        size="md"
      >
        <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
          {executions.map((e) => (
            <div
              key={e.id}
              onClick={() => handleSelectHistoryExecution(e.id)}
              className="p-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] rounded-xl flex items-center justify-between cursor-pointer transition"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-indigo-300 font-bold">{e.id.slice(0, 8)}...</span>
                  <StatusBadge status={e.status} label={e.status.toUpperCase()} />
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  Started: {new Date(e.started_at || e.created_at).toLocaleString()}
                </div>
              </div>
              <ChevronRight size={14} className="text-slate-500" />
            </div>
          ))}
          {executions.length === 0 && (
            <div className="text-center py-8 text-xs text-slate-500">No past executions recorded.</div>
          )}
        </div>
      </Modal>

      {/* Accessible Plain-Text Outline Modal */}
      <Modal
        isOpen={showOutlineModal}
        onClose={() => setShowOutlineModal(false)}
        title={`Accessible Workflow Outline: ${workflow?.name || ''}`}
        description="Linear text-based breakdown of graph nodes, edges, and dependencies for screen readers and linear review."
        size="md"
      >
        <div className="space-y-3">
          <div className="text-xs text-slate-300 space-y-2 max-h-80 overflow-y-auto pr-1">
            {nodes.map((node, idx) => {
              const outEdges = edges.filter((e) => e.source === node.id);
              return (
                <div key={node.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {idx + 1}. {node.data?.name} ({node.data?.node_type})
                    </span>
                    <Badge variant="slate">{node.data?.node_key}</Badge>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Type: <span className="text-indigo-300 font-mono">{node.data?.node_type}</span>
                  </p>
                  {outEdges.length > 0 && (
                    <div className="text-[11px] text-slate-400 mt-1">
                      → Connects to:{' '}
                      {outEdges
                        .map((e) => {
                          const target = nodes.find((n) => n.id === e.target);
                          return target ? target.data?.name : e.target;
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

export default function UserWorkflowEditor(props) {
  return (
    <ReactFlowProvider>
      <WorkflowEditorContent {...props} />
    </ReactFlowProvider>
  );
}
