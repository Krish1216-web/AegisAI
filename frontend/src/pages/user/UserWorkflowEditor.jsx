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
  FileText
} from 'lucide-react';

const nodeTypes = {
  workflowNode: WorkflowNodeComponent
};

function WorkflowEditorContent({ triggerNotification }) {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

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
      if (triggerNotification) triggerNotification('Invalid Connection', 'Self-loops are not allowed in a DAG.');
      return;
    }

    const duplicate = edges.some(
      (e) => e.source === params.source && e.target === params.target
    );
    if (duplicate) {
      if (triggerNotification) triggerNotification('Duplicate Connection', 'Connection already exists.');
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
  }, [edges, nodes, variables, pushHistory, triggerNotification]);

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

  // 12. Save Workflow Definition (Atomic + Optimistic Version Check)
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
      if (triggerNotification) triggerNotification('Workflow Saved', `Saved version ${updated.version} successfully.`);
    } catch (err) {
      console.error('Save failed:', err);
      if (err.status === 409) {
        alert('Workflow was modified by another session. Please reload the latest definition before saving.');
      } else {
        if (triggerNotification) triggerNotification('Save Failed', err.message || 'Validation error');
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
        if (triggerNotification) triggerNotification('Validation Passed', 'Graph topology is valid.');
      }
    } catch (err) {
      console.error('Validation error:', err);
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
        if (triggerNotification) triggerNotification('Workflow Paused', 'Execution is paused.');
      } else {
        const updated = await activateWorkflow(workflow.id);
        setWorkflow(updated);
        if (triggerNotification) triggerNotification('Workflow Activated', 'Ready for live execution.');
      }
    } catch (err) {
      console.error('Status toggle failed:', err);
      if (triggerNotification) triggerNotification('Activation Failed', err.message || 'Cannot activate invalid workflow');
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
        alert('Invalid JSON input format.');
        setIsRunning(false);
        return;
      }
      const res = await executeWorkflow(workflow.id, parsed);
      syncExecutionToNodes(res);
      if (triggerNotification) triggerNotification('Execution Started', `Status: ${res.status}`);
    } catch (err) {
      console.error('Run failed:', err);
      if (triggerNotification) triggerNotification('Execution Failed', err.message || 'Execution error');
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
      if (triggerNotification) triggerNotification('Approval Submitted', `Execution is now ${res.status}`);
    } catch (err) {
      console.error('Approval failed:', err);
      if (triggerNotification) triggerNotification('Approval Error', err.message);
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
      if (triggerNotification) triggerNotification('Execution Cancelled', 'Execution was aborted.');
    } catch (err) {
      console.error('Cancel failed:', err);
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
      <div className="h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 gap-3">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
        <span className="text-xs font-mono uppercase tracking-wider">Loading Workflow Canvas...</span>
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
        onCloneWorkflow={async () => {
          const cloned = await cloneWorkflow(workflow.id);
          navigate(`/user/workflows/${cloned.id}/edit`);
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
            <div className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 border border-slate-800 p-2.5 rounded-2xl backdrop-blur-xl shadow-xl select-none">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-slate-400">Execution:</span>
                <span className="text-xs font-mono text-indigo-300 font-bold">
                  {activeExecution.id.slice(0, 8)}...
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                    activeExecution.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : activeExecution.status === 'running'
                      ? 'bg-indigo-500/20 text-indigo-400 animate-pulse'
                      : activeExecution.status === 'waiting_approval'
                      ? 'bg-amber-500/20 text-amber-400'
                      : activeExecution.status === 'failed'
                      ? 'bg-rose-500/20 text-rose-400'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {activeExecution.status}
                </span>
              </div>

              {activeExecution.status === 'waiting_approval' && (
                <div className="flex items-center gap-1.5 ml-2">
                  <button
                    onClick={() => handleApprove(true)}
                    disabled={isApproving}
                    className="px-2.5 py-1 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1 shadow-sm transition"
                  >
                    <Check className="w-3 h-3" /> Approve
                  </button>
                  <button
                    onClick={() => handleApprove(false)}
                    disabled={isApproving}
                    className="px-2.5 py-1 rounded-xl bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 text-xs font-semibold flex items-center gap-1 transition"
                  >
                    <X className="w-3 h-3" /> Reject
                  </button>
                </div>
              )}

              {activeExecution.status === 'running' && (
                <button
                  onClick={handleCancelExecution}
                  className="px-2 py-1 rounded-xl bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 text-xs font-medium flex items-center gap-1 transition"
                >
                  <StopCircle className="w-3 h-3" /> Cancel
                </button>
              )}

              <button
                onClick={handleOpenHistory}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
                title="Execution History"
              >
                <History className="w-3.5 h-3.5" />
              </button>
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

        {/* Right: Node / Execution Inspector */}
        {selectedNode && (
          <div className="w-96 bg-slate-950 border-l border-slate-800 h-full flex flex-col z-20 shadow-2xl">
            {/* Tab switch if execution exists */}
            {selectedNodeExec && (
              <div className="p-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-200">Execution Output</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold ${
                    selectedNodeExec.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                  }`}>
                    {selectedNodeExec.status}
                  </span>
                </div>
                <button onClick={() => setSelectedNodeId(null)} className="text-slate-400 hover:text-slate-200">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {selectedNodeExec ? (
              <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block mb-1">Node Key</span>
                  <div className="font-mono text-slate-200 bg-slate-900 p-2 rounded-lg border border-slate-800">
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
                  <pre className="p-3 rounded-xl bg-slate-900 border border-slate-800 font-mono text-emerald-400 overflow-x-auto max-h-64">
                    {JSON.stringify(selectedNodeExec.output_data, null, 2)}
                  </pre>
                </div>

                <div className="pt-2 border-t border-slate-800 flex justify-end">
                  <button
                    onClick={() => {
                      // Switch back to edit mode
                      syncExecutionToNodes(null);
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    Edit Node Config &rarr;
                  </button>
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

      {/* Validation Toast/Panel */}
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
      {showRunModal && workflow && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Play className="w-4 h-4 text-cyan-400" />
                Execute Workflow: {workflow.name}
              </h3>
              <button onClick={() => setShowRunModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Input Parameters (JSON)</label>
              <textarea
                value={runInput}
                onChange={(e) => setRunInput(e.target.value)}
                rows={5}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-indigo-300 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {activeExecution && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Execution Output</span>
                  <span className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold ${
                    activeExecution.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : activeExecution.status === 'waiting_approval'
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {activeExecution.status}
                  </span>
                </div>
                <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto max-h-48">
                  {JSON.stringify(activeExecution.output_data || activeExecution.error, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowRunModal(false)}
                className="px-3.5 py-1.5 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-medium"
              >
                Close
              </button>
              <button
                onClick={handleRun}
                disabled={isRunning}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold transition"
              >
                {isRunning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Execute Run
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Execution History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                Execution History
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto space-y-2">
              {executions.map((e) => (
                <div
                  key={e.id}
                  onClick={() => handleSelectHistoryExecution(e.id)}
                  className="p-3 bg-slate-950 hover:bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between cursor-pointer transition"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-indigo-300 font-bold">{e.id.slice(0, 8)}...</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold ${
                        e.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : e.status === 'waiting_approval'
                          ? 'bg-amber-500/20 text-amber-400'
                          : e.status === 'failed'
                          ? 'bg-rose-500/20 text-rose-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {e.status}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">
                      Started: {new Date(e.started_at || e.created_at).toLocaleString()}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500" />
                </div>
              ))}
              {executions.length === 0 && (
                <div className="text-center py-8 text-xs text-slate-500">No past executions found.</div>
              )}
            </div>
          </div>
        </div>
      )}
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
